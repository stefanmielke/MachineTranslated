import requests
from bs4 import BeautifulSoup
import os
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

def get_last_page_number(base_url):
    response = requests.get(base_url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    last_page_link = soup.find("a", string="\u6700\u5f8c\u3078")  # "\u6700\u5f8c\u3078" is "最後へ" in Unicode
    if last_page_link and 'href' in last_page_link.attrs:
        last_page_url = last_page_link['href']
        # Extract page number from the URL
        return int(last_page_url.split("p=")[-1])
    return 1

def get_chapter_links(base_url):
    last_page_number = get_last_page_number(base_url)
    chapter_links = []
    base_url_without_trailing_slash = base_url.rstrip('/')
    
    for page_number in range(1, last_page_number + 1):
        url = f"{base_url}?p={page_number}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Get all chapter links from the current page
        chapter_list = soup.find_all("div", class_="p-eplist__sublist")
        for chapter in chapter_list:
            link = chapter.find("a")
            if link and 'href' in link.attrs:
                full_link = requests.compat.urljoin(base_url_without_trailing_slash + '/', link['href'])
                chapter_links.append(full_link)

    return chapter_links

def save_chapter_text(url, output_folder, index):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    article = soup.find("article")
    if article:
        # Extract text and save to file
        chapter_title = f"chapter_{index:04d}"
        file_path = os.path.join(output_folder, f"{chapter_title}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            # Get chapter title from h1 with class 'p-novel__title'
            title_h1 = article.find("h1", class_="p-novel__title")
            if title_h1:
                title_text = title_h1.get_text(strip=True)
                file.write(f"# {title_text}\n\n")
            
            divs = article.find_all("div", class_="js-novel-text")
            for div in divs:
                if div.has_attr('class') and 'p-novel__text--afterword' in div['class']:
                    file.write("\n\n<b>\n\n----------------\n\n")

                paragraphs = div.find_all("p")
                for paragraph in paragraphs:
                    # Check if paragraph contains an image
                    image = paragraph.find("img")
                    if image:
                        alt_text = image.get("alt", "image")
                        img_url = image.get("src")
                        if img_url:
                            if img_url.startswith("//"):
                                img_url = "https:" + img_url
                            file.write(f"![{alt_text}]({img_url})\n\n")
                    else:
                        text = paragraph.get_text(strip=True)
                        if not text:
                            file.write("<b>\n\n")
                        else:
                            file.write(text + "\n\n")

                if div.has_attr('class') and 'p-novel__text--preface' in div['class']:
                    file.write("\n----------------\n\n<b>\n\n")
        
        # Remove duplicated blank lines and trailing blank lines
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        cleaned_content = re.sub(r'\n{2,}', '\n\n', content).rstrip('\n')
        
        # Write cleaned content back to file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(cleaned_content)

def main(base_url, output_folder):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    chapter_links = get_chapter_links(base_url)
    
    print("Total Chapters Found:", len(chapter_links))
    for index, link in enumerate(chapter_links, start=1):
        print(f"Saving chapter from: {link}")
        save_chapter_text(link, output_folder, index)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python script.py <base_url> <output_folder>")
    else:
        main(sys.argv[1], sys.argv[2])
