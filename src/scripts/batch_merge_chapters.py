import os
import glob
import math
import sys

def merge_txt_files(folder_path):
    # Get a list of all txt files in the folder
    all_txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    
    # Calculate the number of batches needed
    batch_size = 40
    num_batches = math.ceil(len(all_txt_files) / batch_size)

    # Process each batch
    for batch_index in range(num_batches):
        # Get the txt files for the current batch
        start_index = batch_index * batch_size
        end_index = min(start_index + batch_size, len(all_txt_files))
        batch_files = all_txt_files[start_index:end_index]

        # Define output filename for the batch
        output_filename = os.path.join(folder_path, f"merged_batch_{batch_index + 1}.txt")
        
        with open(output_filename, 'w', encoding='utf-8') as output_file:
            for file_path in batch_files:
                filename = os.path.basename(file_path)
                marker = f"%%%%%%%%{filename}\n"
                
                # Write marker to output file
                output_file.write(marker)
                
                # Write content of the file to the output file
                with open(file_path, 'r', encoding='utf-8') as input_file:
                    output_file.write(input_file.read())
                    output_file.write('\n')  # Ensure separation between files
    
    print(f"Successfully merged files into {num_batches} batches.")

# Example usage:
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
    else:
        folder_to_merge = sys.argv[1]
        merge_txt_files(folder_to_merge)
