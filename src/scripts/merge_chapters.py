import os
import sys
import re

def merge_files(jp_dir, en_dir, output_dir):
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Sort filenames to ensure they are processed in order
    filenames = sorted(os.listdir(jp_dir))

    # Loop through all files in the Japanese directory
    for i, filename in enumerate(filenames):
        jp_path = os.path.join(jp_dir, filename)
        en_path = os.path.join(en_dir, filename)

        # Ensure corresponding file exists in English directory
        if not os.path.exists(en_path):
            print(f"Skipping {filename} as there is no corresponding English file.")
            continue

        # Read both Japanese and English files
        with open(jp_path, 'r', encoding='utf-8') as jp_file, open(en_path, 'r', encoding='utf-8') as en_file:
            jp_lines = jp_file.readlines()
            en_lines = en_file.readlines()

        # Ensure both files have the same number of lines
        if len(jp_lines) != len(en_lines):
            print(f"Warning: {filename} has different number of lines in Japanese and English.")
            continue

        # Create the output markdown file
        output_filename = os.path.splitext(filename)[0] + ".md"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as output_file:
            # Add previous and next chapter links
            chapter_number = int(re.search(r'\d+', filename).group())

            if i > 0:
                prev_chapter = os.path.splitext(filenames[i - 1])[0]
                output_file.write(f"###### [Previous Chapter](./{prev_chapter}.md)\n")
            if i < len(filenames) - 1:
                next_chapter = os.path.splitext(filenames[i + 1])[0]
                output_file.write(f"###### [Next Chapter](./{next_chapter}.md)\n")

            output_file.write("\n")  # Add a newline after the links

            # Write content from both Japanese and English files
            for en_line, jp_line in zip(en_lines, jp_lines):
                # If either line contains '<blank>', write it only once
                if jp_line.strip() == "<blank>" or jp_line.strip() == "<b>":
                    output_file.write("&nbsp;\n")
                elif jp_line.strip().startswith("!["):
                    output_file.write(jp_line.strip() + '\n')
                elif jp_line.strip() == "----------------":
                    output_file.write("----------------\n")
                elif jp_line.strip() == "":
                    output_file.write("\n")
                elif jp_line.strip().startswith("#"):
                    output_file.write(en_line.strip() + '\n')
                    output_file.write('\n#' + jp_line.strip() + '\n')
                elif not re.search(r'[一-鿿぀-ゟ゠-ヿA-Za-z0-9「」]', jp_line):  # If jp_line has no Japanese characters, numbers, letters, or brackets
                    output_file.write(jp_line.strip() + '\n')
                else:
                    output_file.write(en_line.strip() + '\n')
                    output_file.write('\n*' + jp_line.strip() + '*\n')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <root_directory>")
        sys.exit(1)

    root_directory = sys.argv[1]
    jp_directory = os.path.join(root_directory, "jp")  # Directory containing Japanese files
    en_directory = os.path.join(root_directory, "en")  # Directory containing English files
    output_directory = os.path.join(root_directory, "out")  # Directory to save merged files

    merge_files(jp_directory, en_directory, output_directory)
    print("All files have been processed.")
