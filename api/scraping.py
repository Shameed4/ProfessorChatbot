import time
import requests
import json
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException
import io
import re
import os
from pathlib import Path

# Replace with the actual URL of the faculty directory
base_url = "https://scholar.google.com"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
}
successful_articles = dict()
unsuccessful_articles = dict()
sleep_time = 0.1

papers_path = Path('./papers')

# Create the directory if it doesn't exist
if not os.path.exists(papers_path):
    os.makedirs(papers_path)


def name2scholar_url(name, college):
    url = f"https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors=+{'+'.join(name.lower().split(' '))}+{'+'.join(college.lower().split(' '))}"
    # Send a GET request to the URL

    time.sleep(sleep_time)
    response = requests.get(url, headers=headers)

    # Check for successful response
    if response.status_code != 200:
        raise ValueError(f"Error {response.status_code}: Failed to retrieve data from {url}")

    soup = BeautifulSoup(response.content, 'html.parser')
    prof_page_html = soup.find('div', class_='gs_scl')
    if prof_page_html is None:
        raise ValueError('Professor Page Not Found')

    prof_url_end = prof_page_html.find('a')['href']
    prof_url = f'{base_url}{prof_url_end}'
    return prof_url


def scholar_url2public_articles_url(scholar_url):
    # Send a GET request to the URL
    time.sleep(sleep_time)
    response = requests.get(scholar_url, headers=headers)

    # Check for successful response
    if response.status_code != 200:
        raise ValueError(f"Error {response.status_code}: Failed to retrieve data from {url}")

    soup = BeautifulSoup(response.content, 'html.parser')
    public_articles_html = soup.find('a', {'id': 'gsc_lwp_mndt_lnk'})
    if public_articles_html is None:
        raise ValueError("No public articles found")
    articles_url = f"{base_url}{public_articles_html['href']}"
    return articles_url


def public_articles_url2article_info(public_articles_url):
    # Send a GET request to the URL
    time.sleep(sleep_time)
    response = requests.get(public_articles_url, headers=headers)

    # Check for successful response
    if response.status_code != 200:
        raise ValueError(f"Error {response.status_code}: Failed to retrieve data from {url}")

    soup = BeautifulSoup(response.content, 'html.parser')
    available_section_html = soup.find('div', class_='gsc_mnd_sec_avl')
    if available_section_html is None:
        raise ValueError(f'No available articles found on {public_articles_url}')
    all_articles_html = available_section_html.find_all('div', class_='gsc_mnd_art')
    all_articles_data = [(article_html.find('span', class_='gsc_mnd_art_ttl').text,
                          article_html.find('a', class_='gsc_mnd_art_access')['href']) for article_html in
                         all_articles_html]
    print(all_articles_data)
    return all_articles_data


def read_pdf(article_name, pdf_url):
    pdf_name = re.sub(r'[\/:*?"<>|]', '_', article_name) + '.txt'
    # Fetching the PDF content
    time.sleep(sleep_time)
    response = requests.get(url=pdf_url, allow_redirects=True, headers=headers, timeout=120)

    on_fly_mem_obj = io.BytesIO(response.content)
    pdf_file = PdfReader(on_fly_mem_obj)
    # Saving the extracted text to a plain text file
    with open(f"{papers_path}/{pdf_name}", 'w', encoding='utf-8') as file:
        for page in pdf_file.pages:
            text = page.extract_text()
            if text:  # Check if there's any text extracted from the page
                text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
                file.write(text)
                file.write("\n")  # Add a newline character after each page's text
        successful_articles[pdf_name] = (article_name, pdf_url)


# def read_mit(article_name, article_url):
#     driver = webdriver.Chrome()  # Replace with your preferred browser
#     driver.get(article_url)
#
#     # try to find a clickable button to a pdf
#     button = None
#     try:
#         # Try to find by ID (corrected to class name)
#         button = WebDriverWait(driver, 0.5).until(
#             EC.element_to_be_clickable((By.CLASS_NAME, "pdf"))
#         )
#     except TimeoutException:
#         driver.close()
#         return False  # If class not found, proceed
#
#     if not button:
#         driver.close()
#         return False
#
#     old_link = button.get_attribute('href')
#     driver.get(old_link)
#     time.sleep(0.5)
#     new_link = driver.current_url
#     response = requests.head(new_link)
#     content_type = response.headers.get('Content-Type')
#     if content_type and 'application/pdf' in content_type:
#         read_pdf(article_name, new_link)
#         driver.close()
#         return True
#     else:
#         driver.close()
#         return False


def read_article(article_name, article_url):
    time.sleep(sleep_time)
    response = requests.head(article_url, allow_redirects=True, headers=headers)
    content_type = response.headers.get('Content-Type')
    if content_type and 'application/pdf' in content_type:
        read_pdf(article_name, article_url)
        return

    # i hate you mit
    # read_mit(article_name, article_url)
    time.sleep(sleep_time)
    response = requests.get(article_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    if 'fullHtml' in article_url:
        try:
            read_pdf(article_name, article_url.replace('fullHtml', 'pdf'))
            return
        except:
            pass

    if 'drive.google.com/file/' in article_url:
        # Regular expression to extract the file ID from the viewing URL
        file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', article_url)
        if not file_id_match:
            raise ValueError("Invalid Google Drive viewing URL")

        file_id = file_id_match.group(1)
        # Construct the direct download URL
        direct_download_url = f'https://drive.google.com/uc?id={file_id}'
        read_pdf(article_name, direct_download_url)
        return

    if 'https://www.ncbi.nlm.nih.gov/' in article_url:
        pdf_url = f"https://www.ncbi.nlm.nih.gov{soup.find('a', class_='int-view')['href']}"
        read_pdf(article_name, pdf_url)
        return

    print('Unsuccessfully handled', article_url)
    unsuccessful_articles[article_name] = article_url


def read_all_articles(article_data):
    for article_name, article_url in article_data:
        read_article(article_name, article_url)
    with open(f'{papers_path}/successful_articles.json', 'w') as file:
        json.dump(successful_articles, file)
    with open(f'{papers_path}/unsuccessful_articles.json', 'w') as file:
        json.dump(unsuccessful_articles, file)

def scrape_professor_by_name_college(professor_name, college="Stony Brook University"):
    global papers_path
    papers_path = papers_path / f"{professor_name.lower().replace(' ', '_')}"
    # Create the directory if it doesn't exist
    if not os.path.exists(papers_path):
        os.makedirs(papers_path)
    scholar_url = name2scholar_url(professor_name, college)
    public_articles_url = scholar_url2public_articles_url(scholar_url)
    article_data = public_articles_url2article_info(public_articles_url)
    read_all_articles(article_data)
    return papers_path

if __name__ == "__main__":
    scrape_professor_by_name_college(input("which professor would you like data on? "), input("which college would you like your data on? "))


