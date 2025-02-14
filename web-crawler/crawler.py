import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
import time

#took help from ChatGPT for regex, threading and checking if pdf is corrupt

BASE_URL = "https://papers.nips.cc/"
SAVE_DIR = "./scrap_downloaded_pdfs"

def create_dir(path):
    os.makedirs(path, exist_ok=True)

def fetch_html_page(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return ""
    return response.text

def extract_links_each_year(html_text):
    years = {}  # Dictionary for storing key pair values
    if html_text:
        beautiful_soup = BeautifulSoup(html_text, 'html.parser')
        for link in beautiful_soup.find_all('a', href=True):
            href_tag = link['href']
            if href_tag.startswith("/paper_files/paper/"):
                year = href_tag.split("/")[-1]
                years[year] = urljoin(BASE_URL, href_tag)
    return years

def clean_filename(filename): #Used ChatGPT
    filename = re.sub(r'[^\w\-]', '_', filename)  # Remove special chars except underscores and dashes
    filename = re.sub(r'_+', '_', filename).strip('_')  # Remove extra underscores
    return filename.replace('.pdf', '')  # Ensure ".pdf" is not in the name

def extract_papers_link(html_text):
    paper_links = {}
    if html_text:
        beautiful_soup = BeautifulSoup(html_text, 'html.parser')
        for link in beautiful_soup.find_all('a', href=True):
            href_tag = link['href']
            if href_tag.startswith("/paper_files/paper/"):
                paper_name = link.text.strip()
                paper_name = clean_filename(paper_name) 
                paper_links[paper_name] = urljoin(BASE_URL, href_tag)
    return paper_links

def extract_pdf_link(html_text):
    pdf_links = []
    if html_text:
        beautiful_soup = BeautifulSoup(html_text, 'html.parser')
        for link in beautiful_soup.find_all('a', href=True):
            if link['href'].endswith(".pdf"):
                pdf_links.append(urljoin(BASE_URL, link['href']))
    return pdf_links

def download_pdf(url, filepath, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=15)  
            response.raise_for_status()
            total_size = int(response.headers.get('Content-Length', 0))
            with open(filepath, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            # Verify file size after download
            downloaded_size = os.path.getsize(filepath)
            if total_size != downloaded_size: #Checking if PDF is not corrupt based on size
                print(f"Warning: File may be corrupted.")
            else:
                print(f"Downloaded: {filepath}")
            break  
        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}. Attempt {attempt+1}/{retries}")
            if attempt < retries - 1:
                print("Retrying...")
                time.sleep(2)  # Wait before retrying
            else:
                print(f"Failed to download {url} after {retries} attempts.")

def extract_paper(paper_name, paper_link, year_dir):
    paper_html_page = fetch_html_page(paper_link)
    if paper_html_page:
        pdf_links = extract_pdf_link(paper_html_page)
        threads = []  
        for pdf_link in pdf_links:
            pdf_filename = os.path.join(year_dir, f"{paper_name}.pdf")
            thread = threading.Thread(target=download_pdf, args=(pdf_link, pdf_filename))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

def main():
    create_dir(SAVE_DIR)
    main_html = fetch_html_page(BASE_URL)
    years_link = extract_links_each_year(main_html)
    
    for year, year_link in years_link.items():
        year_dir = os.path.join(SAVE_DIR, year)
        create_dir(year_dir)

        year_html = fetch_html_page(year_link)
        paper_links = extract_papers_link(year_html)
        
        for paper_name, paper_link in paper_links.items():
            extract_paper(paper_name, paper_link, year_dir)

if __name__ == "__main__":
    main()