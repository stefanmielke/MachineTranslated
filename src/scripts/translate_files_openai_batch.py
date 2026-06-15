import os
import json
import sys

DEFAULT_MODEL = "gpt-5-mini"
BASE_SYSTEM_PROMPT = (
    "You are a literary translator specialist. Translate any message I send you. "
    "Don't add any other text on it. Focus on accuracy. Leave all blank lines as they are. "
    "Do not translate lines with '<b>' or '![text](text)', but leave them as is."
)


def build_system_prompt(extra_system_prompt=""):
    extra_system_prompt = extra_system_prompt.lstrip("\ufeff").strip()
    if not extra_system_prompt:
        return BASE_SYSTEM_PROMPT

    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "Use the following series-specific character, terminology, and setting notes while translating:\n"
        f"{extra_system_prompt}"
    )


def prepare_batch_files(input_folder, model=DEFAULT_MODEL, extra_system_prompt=""):
    # Iterate through all files in the input folder
    output_file_path = os.path.join(input_folder, "batch_requests.jsonl")
    system_prompt = build_system_prompt(extra_system_prompt)
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for filename in os.listdir(input_folder):
            input_file_path = os.path.join(input_folder, filename)
            
            # Check if the path is a file and has a .txt extension
            if os.path.isfile(input_file_path) and filename.endswith('.txt'):
                # Read the content of the file
                with open(input_file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Prepare the batch request in JSON format according to the expected format
                batch_data = {
                    "custom_id": filename,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "temperature": 0.3,
                        "max_tokens": 16384,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": content
                            }
                        ]
                    }
                }
                
                # Write each batch request as a single line in the output file (JSONL format)
                output_file.write(json.dumps(batch_data, ensure_ascii=False) + '\n')
    
    print(f"Batch requests written to {output_file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python script.py <input_folder> [model] [extra_system_prompt_file]")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_MODEL
    extra_system_prompt = ""
    if len(sys.argv) == 4:
        model = sys.argv[2]
        with open(sys.argv[3], "r", encoding="utf-8-sig") as prompt_file:
            extra_system_prompt = prompt_file.read()
    prepare_batch_files(input_folder, model=model, extra_system_prompt=extra_system_prompt)
    print("Batch preparation completed!")
