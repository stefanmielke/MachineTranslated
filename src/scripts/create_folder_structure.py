import os
import sys

def create_translation_structure(translation_id):
    base_path = os.path.join("docs", "translations", translation_id)
    folders = ["jp", "en", "out"]
    config_path = os.path.join("docs", "_config.yml")
    data_json_path = os.path.join(base_path, "data.json")

    # Create folders
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created folder: {folder_path}")

    # Create empty data.json
    open(data_json_path, 'a').close()
    print(f"Created empty file: {data_json_path}")

    # Append paths to config.yaml
    with open(config_path, "a", encoding="utf-8") as config_file:
        config_file.write(f"\n- docs/translations/{translation_id}/data.json")
        config_file.write(f"\n- docs/translations/{translation_id}/en")
        config_file.write(f"\n- docs/translations/{translation_id}/jp")
        print(f"Updated config file: {config_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <id>")
        sys.exit(1)

    translation_id = sys.argv[1]
    create_translation_structure(translation_id)
