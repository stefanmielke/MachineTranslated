import os
import sys

def compare_files(en_folder, jp_folder):
    en_files = {f for f in os.listdir(en_folder) if os.path.isfile(os.path.join(en_folder, f))}
    jp_files = {f for f in os.listdir(jp_folder) if os.path.isfile(os.path.join(jp_folder, f))}

    # Find common files
    common_files = en_files.intersection(jp_files)
    
    for file_name in common_files:
        en_file_path = os.path.join(en_folder, file_name)
        jp_file_path = os.path.join(jp_folder, file_name)

        # Read lines from both files
        with open(en_file_path, 'r', encoding='utf-8') as en_file, open(jp_file_path, 'r', encoding='utf-8') as jp_file:
            en_lines = en_file.readlines()
            jp_lines = jp_file.readlines()

        # Check if line count matches
        if len(en_lines) != len(jp_lines):
            print(f"Line count mismatch in file: {file_name}")

            # Find all mismatched lines containing '<b>'
            idx = 0
            while idx < min(len(en_lines), len(jp_lines)):
                en_line = en_lines[idx]
                jp_line = jp_lines[idx]
                if '<b>' in en_line or '<b>' in jp_line:
                    if en_line != jp_line:
                        print(f"Mismatch found in file '{file_name}' at line {idx + 1}")
                        print(f"en: {en_line.strip()}\njp: {jp_line.strip()}\n")

                        # Insert a new line before the mismatched line in the English file
                        en_lines.insert(idx, "\n<blank>\n")

                idx += 1

            # Overwrite the English file with the updated content
            with open(en_file_path, 'w', encoding='utf-8') as en_file:
                en_file.writelines(en_lines)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compare_files.py <root_directory>")
        sys.exit(1)

    root_directory = sys.argv[1]
    en_directory = os.path.join(root_directory, "en")
    jp_directory = os.path.join(root_directory, "jp")

    compare_files(en_directory, jp_directory)
