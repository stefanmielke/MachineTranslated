import os
import argparse
import time
from openai import OpenAI
import openai

# Function to translate text using GPT-4 API
def translate_text_gpt4(api_key, text, model="gpt-4o-mini"):
    
    client = OpenAI(
        # This is the default and can be omitted
        api_key=api_key,
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a literary translator specialist. Translate any message I send you. Don't add any other text on it. Focus on accuracy. Leave all blank lines as they are. Do not translate lines with '<b>' or '![text](text)', but leave them as is.",
                },
                {
                    "role": "user",
                    "content": f"{text}",
                }
            ],
            model=model,
            max_tokens=16384,  # Reduced to fit current API limits
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"API error: {e}")
        return None

# Main function that processes all text files in a folder
def process_files(input_folder, output_folder, api_key, model="gpt-4o-mini"):
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Loop through each text file in the input directory
    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            # Load the input text
            with open(input_path, 'r', encoding='utf-8') as file:
                text = file.read()
                
            print(f"Translating file: {filename}")
            
            # Translate the text using GPT-4
            translated_text = translate_text_gpt4(api_key, text, model)
            
            # Save the translated text to the output directory
            if translated_text:
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(translated_text)
                print(f"Translated file saved: {output_path}")
            else:
                print(f"Failed to translate file: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate text files using GPT-4 OpenAI API.")
    parser.add_argument("input_folder", type=str, help="Path to the folder containing input text files.")
    parser.add_argument("output_folder", type=str, help="Path to the folder to save translated text files.")
    parser.add_argument("api_key", type=str, help="OpenAI API key.")
    args = parser.parse_args()

    process_files(args.input_folder, args.output_folder, args.api_key)
