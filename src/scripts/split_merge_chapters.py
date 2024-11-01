import os
import re
import sys

def split_files_in_folder(folder_path):
    # Loop through all files in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".out"):
            file_path = os.path.join(folder_path, file_name)
            split_file(file_path, folder_path)

def split_file(file_path, folder_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Regular expression to find the marker "%%%%%%%%filename"
    pattern = r"%%%%%%%%(.*?)\n"
    sections = re.split(pattern, content)

    # The first element is content before the first marker, which we can ignore
    if len(sections) > 1:
        for i in range(1, len(sections), 2):
            filename = sections[i].strip()
            content = sections[i + 1]
            # Remove the last line from the content
            content = '\n'.join(content.splitlines())
            write_split_file(filename, content, folder_path)

def write_split_file(filename, content, folder_path):
    output_file_path = os.path.join(folder_path, f"{filename}")
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(content)
    print(f"Created: {output_file_path}")

def main(folder_path):
    split_files_in_folder(folder_path)
    print("Splitting complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path>")
    else:
        folder_path = sys.argv[1]
        main(folder_path)
