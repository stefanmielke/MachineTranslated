import os
import sys
import json

def create_index(main_folder):
    # Iterate through each subfolder inside the main folder
    for root, dirs, files in os.walk(main_folder):
        if 'out' in dirs:
            out_folder = os.path.join(root, 'out')
            index_file_path = os.path.join(root, 'index.md')
            data_file_path = os.path.join(root, 'data.json')
            
            try:
                # Read the series name from data.json
                series_name = ""
                if os.path.exists(data_file_path):
                    with open(data_file_path, 'r', encoding='utf-8') as data_file:
                        data = json.load(data_file)
                        series_name = data.get("name", "")
                        novel_updates_link = data.get("novel-updates-link", "")
                        source_link = data.get("source-link", "")
                        ml_used = data.get("ml-used", "")
                
                with open(index_file_path, 'w', encoding='utf-8') as index_file:
                    if series_name:
                        index_file.write(f"# {series_name}\n\n")
                    if ml_used:
                        index_file.write(f"###### Translated with {ml_used}\n\n")
                    if novel_updates_link:
                        index_file.write(f"#### [Novel Updates Link]({novel_updates_link})\n\n")
                    if source_link:
                        index_file.write(f"#### [Source Link]({source_link})\n\n")
                    index_file.write("### Chapters:\n\n")

                    # Iterate through each file inside the "out" subfolder
                    for file_name in os.listdir(out_folder):
                        file_path = os.path.join(out_folder, file_name)
                        
                        if os.path.isfile(file_path):
                            with open(file_path, 'r', encoding='utf-8') as current_file:
                                first_line = current_file.readline().strip()
                                index_file.write(f"- [{first_line[2:]}](out/{file_name})\n")

                print(f"Created index.md in {root}")
            except Exception as e:
                print(f"Error processing folder {root}: {e}")

def main():
    # Check if a main folder argument is provided
    if len(sys.argv) != 2:
        print("Usage: python create_index.py <main_folder>")
        sys.exit(1)

    main_folder = sys.argv[1]

    # Verify if the provided folder exists
    if not os.path.exists(main_folder):
        print(f"Error: Folder '{main_folder}' does not exist.")
        sys.exit(1)

    # Call the function to create index files
    create_index(main_folder)

if __name__ == "__main__":
    main()
