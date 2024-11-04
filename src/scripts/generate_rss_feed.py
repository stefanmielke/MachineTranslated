import os
import json
import time
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
import sys

# Name of the RSS feed file
RSS_FILE = "feed.xml"
# JSON file containing metadata
JSON_FILE = "data.json"

# CDATA handling
ET._original_serialize_xml = ET._serialize_xml

def CDATA(text=None):
    element = ET.Element('![CDATA[')
    element.text = text
    return element

def _serialize_xml(write, elem, qnames, namespaces, short_empty_elements, **kwargs):
    if elem.tag == '![CDATA[':
        write(f"<![CDATA[{elem.text}]]>")
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
    else:
        return ET._original_serialize_xml(write, elem, qnames, namespaces, short_empty_elements, **kwargs)

ET._serialize_xml = ET._serialize['xml'] = _serialize_xml

# Function to create a unique identifier for each file
def generate_guid(file_path):
    # Generate a unique GUID for each file using its path and modification time
    return hashlib.md5(file_path.encode()).hexdigest()

# Function to add new items to RSS feed
def add_new_items_to_rss(starting_path):
    # Root folder containing multiple series
    series_root_folder = starting_path

    # Create the root element if RSS file doesn't exist
    rss_file_path = os.path.join(series_root_folder, '..', RSS_FILE)
    if not os.path.exists(rss_file_path):
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "Machine Translated Series Feed"
        ET.SubElement(channel, "link").text = f"https://stefanmielke.github.io/MachineTranslated/translations"
        ET.SubElement(channel, "description").text = "Feed of newly added files in multiple series folders."
        tree = ET.ElementTree(rss)
    else:
        # Parse existing RSS file
        tree = ET.parse(rss_file_path)
        rss = tree.getroot()
        channel = rss.find("channel")
    
    # Get the list of GUIDs already present in the feed
    existing_guids = {item.find("guid").text for item in channel.findall("item")}
    
    # Iterate over each series folder
    for series_folder in os.listdir(series_root_folder):
        series_path = os.path.join(series_root_folder, series_folder)
        if os.path.isdir(series_path):
            # Folder containing the files
            out_folder = os.path.join(series_path, "out")
            
            # Load the JSON metadata file for each series
            json_file_path = os.path.join(series_path, JSON_FILE)
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as json_file:
                    metadata = json.load(json_file)
            else:
                metadata = {"name": "No Title Name Found"}
            
            # Add new files to the feed
            new_files = False
            if os.path.exists(out_folder):
                for file_name in os.listdir(out_folder):
                    file_path = os.path.join(out_folder, file_name)
                    if os.path.isfile(file_path):
                        # Extract chapter name from the file
                        with open(file_path, 'r', encoding='utf-8') as current_file:
                            chapter_name = current_file.readline().strip()
                            while not chapter_name.startswith("# "):
                                chapter_name = current_file.readline().strip()

                        guid = generate_guid(file_path)
                        if guid not in existing_guids:
                            new_files = True
                            item = ET.SubElement(channel, "item")
                            title_element = ET.SubElement(item, "title")
                            title_element.append(CDATA(chapter_name[2:]))
                            
                            link_element = ET.SubElement(item, "link")
                            link_element.text = f"https://stefanmielke.github.io/MachineTranslated/translations/{series_folder}/out/{os.path.splitext(file_name)[0]}.html"
                            
                            description_element = ET.SubElement(item, "description")
                            description_element.append(CDATA(f"Chapter '{chapter_name[2:]}' added."))
                            
                            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
                            ET.SubElement(item, "guid").text = guid
                            ET.SubElement(item, "category").text = metadata.get("name", "No Title Name Found")
            
            # Write updated RSS file only if new files were added
            if new_files:
                tree.write(rss_file_path, encoding="utf-8", xml_declaration=True)

# Run the script
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <starting_path>")
    else:
        starting_path = sys.argv[1]
        add_new_items_to_rss(starting_path)