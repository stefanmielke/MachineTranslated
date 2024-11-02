import os
import json
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description="Process a batch output file and create individual files from it.")
parser.add_argument('input_file', type=str, help='Path to the input batch output file')
args = parser.parse_args()

# Define the path to the input file and the folder to save output files
input_file_path = args.input_file
output_folder_path = os.path.dirname(input_file_path)

# Create output folder if it doesn't exist
os.makedirs(output_folder_path, exist_ok=True)

# Process the input file line by line
with open(input_file_path, 'r', encoding='utf-8') as input_file:
    for line_number, line in enumerate(input_file, start=1):
        line = line.strip()
        if not line:
            continue  # Skip empty lines

        try:
            # Parse the JSON object from the line
            result = json.loads(line)

            # Extract the custom_id and the content
            custom_id = result.get('custom_id')
            content = result.get('response', {}).get('body', {}).get('choices', [{}])[0].get('message').get('content')

            # Check if both custom_id and content are available
            if custom_id is None:
                print(f"Warning: Missing custom_id at line {line_number}")
                continue
            if content is None:
                print(f"Warning: Missing content at line {line_number}")
                continue

            # Define the output file path
            output_file_path = os.path.join(output_folder_path, f"{custom_id}")

            # Write the content to the output file
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write(content)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON at line {line_number}: {e}")
        except Exception as e:
            print(f"Unexpected error at line {line_number}: {e}")

print("Processing complete.")
