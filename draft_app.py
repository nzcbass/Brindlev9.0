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
from datetime import timedelta  # if needed elsewhere
from file_tracker import track_file, print_summary
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
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file_route():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        track_file(file_path, "upload", "saved", "File uploaded by user")

        # Process the file (assuming process_cv_pipeline is your processing function)
        response = process_cv_pipeline(file_path, filename)
        
        return jsonify(response)

    return jsonify({"success": False, "message": "Invalid file type"})

def save_enriched_json(enriched_data, base_name):
    enriched_json_path = os.path.join('parsed_jsons', f"{base_name}_enriched.json")
    with open(enriched_json_path, 'w') as file:
        json.dump(enriched_data, file, indent=4)
    return enriched_json_path

def process_cv_pipeline(file_path, filename):
    """
    Process the CV through the complete pipeline.
    Returns a dictionary with the status and results.
    """
    # Track the start of pipeline processing 
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    track_file(file_path, "pipeline", "starting", f"Processing CV: {base_name}")
    
    try:
        print(f"DEBUG: Starting CV pipeline with file: {file_path}")
        
        # Stage 1 - Upload to Firebase
        print(f"DEBUG: Stage 1 - Uploading to Firebase")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        temp_file.close()
        
        shutil.copy2(file_path, temp_file.name)
        firebase_path = firebase_config.upload_file(temp_file.name, f"{base_name}.docx")
        track_file(firebase_path, "firebase", "uploaded", "File uploaded to Firebase")
        
        # Stage 2 - Parse CV
        print(f"DEBUG: Stage 2 - Parsing CV")
        parsed_json_path = send_to_cv_parser(firebase_path)
        if isinstance(parsed_json_path, dict):
            parsed_json_path = parsed_json_path.get('path', '')
        track_file(parsed_json_path, "parse", "parsed", "CV parsed to JSON")
        
        # Stage 3 - Generate blurb
        print(f"DEBUG: Stage 3 - Generating blurb")
        enriched_json_result = generate_blurb_with_claude(parsed_json_path)
        if isinstance(enriched_json_result, dict):
            enriched_json_path = enriched_json_result.get('path', '')
        else:
            enriched_json_path = enriched_json_result
        if not enriched_json_path:
            raise FileNotFoundError("Enriched JSON path is empty")
        track_file(enriched_json_path, "blurb", "generated", "Blurb generated and added to JSON")
        
        # Stage 4 - Classify locations
        print(f"DEBUG: Stage 4 - Classifying locations")
        location_service = LocationService()
        with open(enriched_json_path, 'r') as file:
            enriched_data = json.load(file)
        enriched_data = location_service.enrich_experience_locations(enriched_data)
        
        track_file(enriched_json_path, "locations", "classified", "Locations classified in JSON")
        
        # Stage 5 - Save enriched JSON
        print(f"DEBUG: Stage 5 - Saving enriched JSON")
        enriched_json_path = save_enriched_json(enriched_data, base_name)
        track_file(enriched_json_path, "enrich", "saved", "Enriched JSON saved")
        
        # Stage 5b - (Optional) Extract projects
        projects_data = {}
        extract_projects = False  # Change to True to enable project extraction
        
        if extract_projects:
            print(f"DEBUG: Stage 5b - Extracting projects")
            project_extractor = ProjectExtractor()
            projects_data = project_extractor.extract_projects(enriched_data)
        
        # Stage 6 - Generate document
        print(f"DEBUG: Stage 6 - Generating document")
        template_path = '/Users/claytonbadland/flask_project/templates/Current_template.docx'
        generator = DocGenerator(template_path)
        output_path = generator.generate_cv_document(enriched_json_path, projects_data)
        if not output_path:
            raise Exception("Failed to generate CV document using the template")
        
        # Final step: Save document to Downloads folder
        try:
            if os.path.exists(output_path):
                download_path = save_output_to_downloads(output_path)
                track_file(download_path, "download", "saved", "File saved to Downloads folder")
                download_url = f"/download/{os.path.basename(output_path)}"
            else:
                print(f"Generated file not found at {output_path}")
                return {"success": False, "message": "Generated file not found"}
                
        except Exception as e:
            print(f"Error saving to downloads: {str(e)}")
            return {"success": False, "message": f"Error saving to downloads: {str(e)}"}

        return {
            'success': True,
            'message': f'CV processed: {filename}',
            'download_file': os.path.basename(output_path),
            'download_url': download_url
        }
        
    except Exception as e:
        print(f"Error in CV pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"Error processing CV: {str(e)}"}

@app.route('/download/<filename>')
def download_file(filename):
    """Serve the file for download"""
    return send_from_directory(os.path.join(app.root_path, 'outputs'),
                              filename, as_attachment=True)

@app.route('/download-processed/<path:filename>')
def download_processed_cv(filename):
    try:
        # Extract base name without extension
        base_name = Path(filename).stem
        if base_name.endswith("_enriched"):
            base_name = base_name[:-9]   # Remove _enriched suffix
        
        print(f"Processing download for base name: {base_name}")
        
        local_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{base_name}_processed.docx")
        if os.path.exists(local_path):
            print(f"✅ Found document locally at: {local_path}")
            
            # Track the download
            track_file(local_path, "download", "local", "Downloading local file")
            
            return send_file(
                local_path,
                as_attachment=True,
                download_name=f"{base_name}_CV.docx",  # Clean filename for user
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        return "Could not find the document", 404
        
    except Exception as e:
        print(f"Error in download_processed_cv: {e}")
        import traceback
        traceback.print_exc()
        return f"Error processing request: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)