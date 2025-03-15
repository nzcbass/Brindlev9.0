from firebase_utils import FirebaseConfig

# Instantiate FirebaseConfig so we can call its methods.
firebase_config = FirebaseConfig()

def format_company_and_position_placeholders(placeholder_mapping: dict) -> dict:
    """
    Formats placeholders for consistent capitalization and formatting:
    - List items: Converts to bullet points with proper capitalization
    - Text fields: Ensures proper capitalization (first letter uppercase, rest lowercase)
    """
    # Format bullet-pointed lists
    keys_to_format = [
        "{InternationalEmployers}",
        "{NZEmployers}",
        "{NZPositions}",
        "{InternationalPositions}",
        # Add Qualifications to the bullet-point formatting list
        "{Qualifications}"
    ]
    
    for key in keys_to_format:
        value = placeholder_mapping.get(key, "")
        # Skip formatting if the value is empty or 'None'
        if not value or value.strip().lower() == "none":
            continue

        # Split the string on semicolons
        items = [item.strip() for item in value.split(";") if item.strip()]
        deduped = []
        seen = set()
        for item in items:
            # Convert each item to title case
            formatted_item = item.title()
            # Remove duplicates (case-insensitive)
            if formatted_item.lower() not in seen:
                deduped.append(formatted_item)
                seen.add(formatted_item.lower())
        # Join items as a bullet list
        bullet_list = "\n".join(["• " + item for item in deduped])
        placeholder_mapping[key] = bullet_list if bullet_list else "None"
    
    # Format simple text fields with proper capitalization
    keys_to_capitalize = [
        "{FullName}",
        "{Position}",
        "{CurrentLocation}"
        # Removed Qualifications from here since it's now in keys_to_format
    ]
    
    for key in keys_to_capitalize:
        value = placeholder_mapping.get(key, "")
        if not value or value.strip().lower() == "none":
            continue
        # Title case for these fields (first letter of each word uppercase)
        placeholder_mapping[key] = value.title()
        
    return placeholder_mapping

# Example testing
if __name__ == "__main__":
    sample_mapping = {
        "{InternationalEmployers}": "ABC Company; abc company; XYZ Corp; xyz corp",
        "{NZEmployers}": "KEANGMAN, ENTERPRISES LTD.; NZ Company; nz company; ABC",
        "{NZPositions}": "Senior Developer; Senior Developer; Lead Engineer",
        "{InternationalPositions}": "Manager; Manager; Director",
        "{FullName}": "JOHN DOE",
        "{Position}": "SOFTWARE ENGINEER",
        "{CurrentLocation}": "SYDNEY, AUSTRALIA",
        "{Qualifications}": "BACHELOR OF SCIENCE; MASTER OF SCIENCE"
    }
    formatted_mapping = format_company_and_position_placeholders(sample_mapping)
    print("Formatted mapping:")
    for k, v in formatted_mapping.items():
        print(f"{k}:\n{v}\n")
        
def format_company_and_position_placeholders(placeholder_mapping: dict) -> dict:
    """
    Formats placeholders for consistent capitalization and formatting:
    - List items: Converts to bullet points with proper capitalization
    - Text fields: Ensures proper capitalization (first letter uppercase, rest lowercase)
    """
    # Format bullet-pointed lists
    keys_to_format = [
        "{InternationalEmployers}",
        "{NZEmployers}",
        "{NZPositions}",
        "{InternationalPositions}",
        "{Qualifications}"  # Make sure this is included
    ]
    
    for key in keys_to_format:
        value = placeholder_mapping.get(key, "")
        # Skip formatting if the value is empty or 'None'
        if not value or value.strip().lower() == "none":
            continue

        # Split the string on semicolons
        items = [item.strip() for item in value.split(";") if item.strip()]
        deduped = []
        seen = set()
        for item in items:
            # Convert each item to title case
            formatted_item = item.title()
            # Remove duplicates (case-insensitive)
            if formatted_item.lower() not in seen:
                deduped.append(formatted_item)
                seen.add(formatted_item.lower())
        # Join items as a bullet list
        bullet_list = "\n".join(["• " + item for item in deduped])
        placeholder_mapping[key] = bullet_list if bullet_list else "None"
    
    # Format simple text fields with proper capitalization
    keys_to_capitalize = [
        "{FullName}",
        "{Position}",
        "{CurrentLocation}"
    ]
    
    for key in keys_to_capitalize:
        value = placeholder_mapping.get(key, "")
        if not value or value.strip().lower() == "none":
            continue
        # Title case for these fields (first letter of each word uppercase)
        placeholder_mapping[key] = value.title()
        
    return placeholder_mapping

def format_name(name_str):
    """
    Format a name string: First letter of each word capitalized, rest lowercase.
    """
    if not name_str:
        return ""
    return name_str.title()

def format_template(template_data: str) -> str:
    """
    Format the template data and upload the formatted result to Firebase Storage.
    
    In this example, we simply transform the text to uppercase,
    encode it as bytes, and upload it with the filename 'formatted_template.txt'.
    The function returns the public URL of the uploaded file.
    """
    formatted_data = template_data.upper().encode("utf-8")
    public_url = firebase_config.upload_file(destination_blob_name="formatted_template.txt", data=formatted_data)
    return public_url


if __name__ == "__main__":
    sample_mapping = {
        "{InternationalEmployers}": "ABC Company; abc company; XYZ Corp; xyz corp",
        "{NZEmployers}": "KEANGMAN, ENTERPRISES LTD.; NZ Company; nz company; ABC",
        "{NZPositions}": "Senior Developer; Senior Developer; Lead Engineer",
        "{InternationalPositions}": "Manager; Manager; Director",
        "{FullName}": "JOHN DOE",
        "{Position}": "SOFTWARE ENGINEER",
        "{CurrentLocation}": "SYDNEY, AUSTRALIA",
        "{Qualifications}": "BACHELOR OF SCIENCE; MASTER OF SCIENCE"
    }
    formatted_mapping = format_company_and_position_placeholders(sample_mapping)
    print("Formatted mapping:")
    for k, v in formatted_mapping.items():
        print(f"{k}:\n{v}\n")
    
    # -----------------------------------------------------------
    # Example testing for template formatting and upload to Firebase Storage.
    # -----------------------------------------------------------
    sample_template = "Hello, this is a template."
    template_url = format_template(sample_template)
    print("Formatted template available at:", template_url)