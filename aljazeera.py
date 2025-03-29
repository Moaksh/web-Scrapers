from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from pymongo import MongoClient


uri = "" #add your mongouri
client = MongoClient(uri)
db = client["aljazeera"]
collection = db["articles"]
checkpoint_collection = db["checkpoints"]

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.aljazeera.com/sitemap")

# ---------------------------------- tag links ----------------------------------
print("Fetching tags from the sitemap...")

topics_section = driver.find_element(By.CSS_SELECTOR, '#Tags')


links = topics_section.find_elements(By.TAG_NAME, 'a')


link_data = []
for link in links:
    link_text = link.text
    link_href = link.get_attribute('href')
    link_data.append({'Tag': link_text, 'Tag_link': link_href})

print(f"Found {len(link_data)} tags. Starting to fetch articles...")


last_processed = checkpoint_collection.find_one({}, sort=[("timestamp", -1)])
if last_processed:
    last_tag = last_processed['tag']
    last_processed_count = last_processed['processed_count']
    last_tag_index = next((i for i, link in enumerate(link_data) if link['Tag'] == last_tag), 0)
else:
    last_tag_index = 0
    last_processed_count = 0

# ---------------------------------- inside tags ----------------------------------
# Loop through the link data one by one and scrape the articles
for index in range(last_tag_index, len(link_data)):
    link = link_data[index]
    print(f"Fetching articles for tag: {link['Tag']} ({link['Tag_link']})")
    driver.get(link['Tag_link'])
    time.sleep(2)


    while True:
        try:

            show_more_button = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'show-more-button'))
            )


            driver.execute_script("arguments[0].scrollIntoView();", show_more_button)
            time.sleep(1)


            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'show-more-button'))
            )
            show_more_button.click()
            time.sleep(2)
            print("Clicked 'Show More' button.")
        except Exception as e:
            print("No more articles to load or an error occurred:", str(e))
            break


    articles = driver.find_elements(By.CSS_SELECTOR, '.gc--type-post')
    article_data = []

    for article in articles:
        article_title = article.find_element(By.CSS_SELECTOR, '.u-clickable-card__link').text
        article_url = article.find_element(By.CSS_SELECTOR, '.u-clickable-card__link').get_attribute('href')


        if collection.find_one({'url': article_url}):
            print(f"Article already exists in the database: {article_title}. Skipping...")
            continue


        article_data.append({
            'title': article_title,
            'url': article_url
        })

    print(f"Found {len(article_data)} articles for tag: {link['Tag']}.")


    for article in article_data:
        for attempt in range(3):
            try:
                driver.get(article['url'])
                time.sleep(2)


                title = driver.find_element(By.CSS_SELECTOR, '.article-header h1').text
                try:
                    description = driver.find_element(By.CSS_SELECTOR, 'p.article__subhead').text
                except Exception:
                    description = "NULL"
                paragraphs = driver.find_elements(By.CSS_SELECTOR, '.wysiwyg--all-content p')
                text = ' '.join([para.text for para in paragraphs])
                date_element = driver.find_element(By.CSS_SELECTOR, 'div.date-simple')
                date = date_element.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]').text

                try:
                    source_element = driver.find_element(By.CSS_SELECTOR, '.article-source')
                    source = source_element.text.replace("Source: ", "").strip()
                except Exception:
                    source = "Anonymous"

                try:
                    author_element = driver.find_element(By.CSS_SELECTOR, '.article-author-name-item a')
                    author = author_element.text
                except Exception:
                    author = "Anonymous"


                if description == "NULL":
                    article_doc = {
                        'title': title,
                        'url': article['url'],
                        'author': author,
                        'date': date,
                        'source': source,
                        'text': text,
                        'tag': link['Tag']
                    }
                else:
                    article_doc = {
                        'title': title,
                        'url': article['url'],
                        'description': description,
                        'author': author,
                        'date': date,
                        'source': source,
                        'text': text,
                        'tag': link['Tag']
                    }


                collection.insert_one(article_doc)
                print(f"Inserted article: {title} into MongoDB for tag: {link['Tag']}.")


                checkpoint_collection.update_one(
                    {'tag': link['Tag']},
                    {'$inc': {'processed_count': 1}, '$set': {'timestamp': time.time()}},
                    upsert=True
                )
                break
            except Exception as e:
                print(f"Error scraping article at {article['url']} (attempt {attempt + 1}): {str(e)}")
                time.sleep(2)
                if attempt == 2:
                    print(f"Failed to scrape article at {article['url']} after 3 attempts.")

driver.quit()
print("Browser closed. Scraping completed.")
