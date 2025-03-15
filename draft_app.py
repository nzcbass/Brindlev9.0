from flask import Flask, request, jsonify, send_from_directory, render_template, send_file
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from firebase_utils import FirebaseConfig
from validators import validate_json
from cv_parser import send_to_cv_parser
from claude_utils import generate_blurb_with_claude
from doc_generator import DocGenerator
from location_service import LocationService
from d_projects_to_enriched import ProjectExtractor
from direct_download import save_output_to_downloads
from datetime import timedelta
from file_tracker import track_file, print_summary
from logger import log_info, log_error, log_warning
import tempfile
import shutil
import json

app = Flask(__name__)
firebase_config = FirebaseConfig()

# Create required directories
for path in ['uploads', 'parsed_jsons', 'outputs']:
    Path(path).mkdir(exist_ok=True)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    log_info("Accessing index page")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file_route():
    try:
        if 'file' not in request.files:
            log_warning("No file part in the request")
            return jsonify({"success": False, "message": "No file uploaded. Please select a file."})
        
        file = request.files['file']
        
        if file.filename == '':
            log_warning("No selected file")
            return jsonify({"success": False, "message": "No file selected. Please choose a file to upload."})
        
        if not allowed_file(file.filename):
            log_warning(f"Invalid file type: {file.filename}")
            return jsonify({
                "success": False, 
                "message": f"Invalid file type. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}"
            })
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        log_info(f"Saving uploaded file: {filename}")
        file.save(file_path)
        track_file(file_path, "upload", "saved", "File uploaded by user")

        # Process the file
        log_info(f"Processing file: {filename}")
        response = process_cv_pipeline(file_path, filename)
        
        return jsonify(response)

    except Exception as e:
        log_error("Error in file upload", e)
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your file. Please try again."
        })

def process_cv_pipeline(file_path: str, filename: str) -> dict:
    """Process the CV through the complete pipeline with error handling."""
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        log_info(f"Starting CV pipeline for: {filename}")
        track_file(file_path, "pipeline", "starting", f"Processing CV: {base_name}")
        
        # Stage 1 - Upload to Firebase
        log_info("Stage 1 - Uploading to Firebase")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        temp_file.close()
        
        shutil.copy2(file_path, temp_file.name)
        firebase_path = firebase_config.upload_file(temp_file.name, f"{base_name}.docx")
        if not firebase_path:
            raise Exception("Failed to upload file to Firebase")
        track_file(firebase_path, "firebase", "uploaded", "File uploaded to Firebase")
        
        # Stage 2 - Parse CV
        log_info("Stage 2 - Parsing CV")
        parsed_json_path = send_to_cv_parser(firebase_path)
        if not parsed_json_path:
            raise Exception("Failed to parse CV")
        if isinstance(parsed_json_path, dict):
            parsed_json_path = parsed_json_path.get('path', '')
        track_file(parsed_json_path, "parse", "parsed", "CV parsed to JSON")
        
        # Stage 3 - Generate blurb
        log_info("Stage 3 - Generating blurb")
        enriched_json_result = generate_blurb_with_claude(parsed_json_path)
        if isinstance(enriched_json_result, dict):
            enriched_json_path = enriched_json_result.get('path', '')
        else:
            enriched_json_path = enriched_json_result
        if not enriched_json_path:
            raise Exception("Failed to generate blurb")
        track_file(enriched_json_path, "blurb", "generated", "Blurb generated and added to JSON")
        
        # Stage 4 - Classify locations
        log_info("Stage 4 - Classifying locations")
        location_service = LocationService()
        with open(enriched_json_path, 'r') as file:
            enriched_data = json.load(file)
        enriched_data = location_service.enrich_experience_locations(enriched_data)
        
        # Stage 5 - Save enriched JSON
        log_info("Stage 5 - Saving enriched JSON")
        enriched_json_path = os.path.join('parsed_jsons', f"{base_name}_enriched.json")
        with open(enriched_json_path, 'w') as file:
            json.dump(enriched_data, file, indent=4)
        track_file(enriched_json_path, "enrich", "saved", "Enriched JSON saved")
        
        # Stage 6 - Generate document
        log_info("Stage 6 - Generating document")
        template_path = '/Users/claytonbadland/flask_project/templates/Current_template.docx'
        generator = DocGenerator(template_path)
        output_path = generator.generate_cv_document(enriched_json_path)
        if not output_path:
            raise Exception("Failed to generate CV document")
        
        # Final step: Save document to Downloads folder
        log_info("Saving document to Downloads folder")
        if os.path.exists(output_path):
            download_path = save_output_to_downloads(output_path)
            if not download_path:
                raise Exception("Failed to save file to Downloads folder")
            track_file(download_path, "download", "saved", "File saved to Downloads folder")
            download_url = f"/download/{os.path.basename(output_path)}"
        else:
            raise FileNotFoundError(f"Generated file not found at {output_path}")

        log_info(f"CV processing completed successfully for: {filename}")
        return {
            'success': True,
            'message': f'CV processed successfully: {filename}',
            'download_file': os.path.basename(output_path),
            'download_url': download_url
        }
        
    except Exception as e:
        log_error(f"Error processing CV: {filename}", e)
        return {
            "success": False,
            "message": f"Error processing CV: {str(e)}"
        }

@app.route('/download/<filename>')
def download_file(filename):
    """Serve the file for download with error handling."""
    try:
        log_info(f"Initiating download for: {filename}")
        return send_from_directory(
            os.path.join(app.root_path, 'outputs'),
            filename, 
            as_attachment=True
        )
    except Exception as e:
        log_error(f"Error downloading file: {filename}", e)
        return jsonify({
            "success": False,
            "message": "Error downloading file. Please try again."
        })

@app.errorhandler(413)
def request_entity_too_large(error):
    log_warning("File too large uploaded")
    return jsonify({
        "success": False,
        "message": "File too large. Maximum size is 16MB."
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    log_error("Internal server error", error)
    return jsonify({
        "success": False,
        "message": "An internal server error occurred. Please try again later."
    }), 500

if __name__ == '__main__':
    log_info("Starting CV Generator application")
    app.run(debug=True)
