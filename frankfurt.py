import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchFrameException, WebDriverException

def identify_span_type(span_text):
    if "Sanga:" in span_text:
        return "Sanga"
    elif "Strophe:" in span_text:
        return "Strophe"
    elif "Verse:" in span_text:
        return "Verse"
    else:
        return "text"

def pageReader(driver, start_from_span=0, current_Chapter=None, current_Paragraph=None, current_Verse=None, current_Sentence=None):
    data = []

    try:
        # Switch to the main frame where the content is located
        try:
            driver.switch_to.frame("etatext")
        except NoSuchFrameException:
            print("Frame 'etatext' not found. Trying default content.")
            driver.switch_to.default_content()

        # Wait until at least one span element is present
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span")))

        # Find all span elements using XPath
        span_elements = driver.find_elements(By.XPATH, "//span")
        print(f"Found {len(span_elements)} span elements")

        for index, span in enumerate(span_elements):
            if index < start_from_span:
                continue

            span_text = span.text.strip()
            print(f"Span {index}: {span_text}")

            span_type = identify_span_type(span_text)

            if span_type == "Sanga":
                current_Chapter = span_text.split(': ')[-1]
            elif span_type == "Strophe":
                current_Paragraph = span_text.split(': ')[-1]
            elif span_type == "Verse":
                current_Sentence = span_text.split(': ')[-1]
            else:
                # Filter out noise and unwanted text
                if "This text is part of the TITUS edition" in span_text:
                    continue
                if "Kathā" in span_text:
                    continue

                if current_Chapter and current_Paragraph and current_Sentence:
                    data.append({
                        "Sanga": current_Chapter,
                        "Strophe": current_Paragraph,
                        # "Verse": current_Verse,
                        "Verse": current_Sentence,
                        "text": span_text
                    })
                    # Debug print statement to show what is being added
                    # print(f"Added text: {span_text} | Chapter: {current_Chapter}, Paragraph: {current_Paragraph}, Verse: {current_Verse}, Sentence: {current_Sentence}")
                    print(f"Added text: {span_text} | Chapter: {current_Chapter}, Paragraph: {current_Paragraph}, Sentence: {current_Sentence}")


        # Switch back to the default content
        driver.switch_to.default_content()

    except TimeoutException as e:
        print(f"TimeoutException: {e}")
    except WebDriverException as e:
        print(f"WebDriverException: {e}")

    return data, current_Chapter, current_Paragraph, current_Verse, current_Sentence

def combine_entries_hierarchical(data):
    combined_data = {}

    for entry in data:
        chapter = f"Sanga {entry['Sanga']}"
        paragraph = f"Strophe {entry['Strophe']}"
        # verse = f"Verse {entry['Verse']}"
        sentence = f"Verse {entry['Verse']}"
        text = entry["text"]

        if chapter not in combined_data:
            combined_data[chapter] = {}

        if paragraph not in combined_data[chapter]:
            combined_data[chapter][paragraph] = {}

        # if verse not in combined_data[chapter][paragraph]:
        #     combined_data[chapter][paragraph][verse] = {}

        if sentence not in combined_data[chapter][paragraph]:
            combined_data[chapter][paragraph][sentence] = text
        else:
            combined_data[chapter][paragraph][sentence] += " " + text

    return combined_data

def save_checkpoint(page_number, span_index, data, current_Chapter, current_Paragraph, current_Verse, current_Sentence):
    checkpoint = {
        "page_number": page_number,
        "span_index": span_index,
        "data": data,
        "current_Chapter": current_Chapter,
        "current_Paragraph": current_Paragraph,
        "current_Verse": current_Verse,
        "current_Sentence": current_Sentence
    }
    with open('checkpoint.json', 'w', encoding='utf-8') as file:
        json.dump(checkpoint, file, ensure_ascii=False, indent=4)
    print(f"Checkpoint saved: {checkpoint}")

def load_checkpoint():
    if os.path.exists('checkpoint.json'):
        with open('checkpoint.json', 'r', encoding='utf-8') as file:
            checkpoint = json.load(file)
            return checkpoint['page_number'], checkpoint['span_index'], checkpoint['data'], checkpoint['current_Chapter'], checkpoint['current_Paragraph'], checkpoint['current_Verse'], checkpoint['current_Sentence']
    else:
        return 1, 0, [], None, None, None, None

def save_metadata(metadata):
    with open('metadata_checkpoint.json', 'w', encoding='utf-8') as file:
        json.dump(metadata, file, ensure_ascii=False, indent=4)
    print("Metadata saved")

def load_metadata():
    if os.path.exists('metadata_checkpoint.json'):
        with open('metadata_checkpoint.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        return None

def collect_metadata():
    metadata = {}
    metadata['Title'] = input("Enter the book name: ")
    metadata['Subtitle'] = input("Enter the book Subtitle: ")
    metadata['Editor'] = input("Enter the book editor: ")
    metadata['Publication'] = input("Enter the book publication: ")
    return metadata

def main():
    driver = webdriver.Firefox()

    start_page, start_span, all_data, current_Chapter, current_Paragraph, current_Verse, current_Sentence = load_checkpoint()
    metadata = load_metadata()
    if metadata is None:
        metadata = collect_metadata()
        save_metadata(metadata)

    try:
        base_url = 'http://titus.uni-frankfurt.de/texte/etcs/ind/aind/klskt/kalidasa/kumara/kumar.htm?kumar'
        end_page = 8

        for page_number in range(start_page, end_page + 1):
            formatted_page_number = f"{page_number:03}"
            url = f"{base_url}{formatted_page_number}.htm"
            driver.get(url)
            print(f"Reading page: {formatted_page_number}")

            start_from_span = 0 if page_number == 1 else 0
            if page_number == start_page:
                start_from_span = start_span

            page_data, current_Chapter, current_Paragraph, current_Verse, current_Sentence = pageReader(driver, start_from_span=start_from_span, current_Chapter=current_Chapter, current_Paragraph=current_Paragraph, current_Verse=current_Verse, current_Sentence=current_Sentence)
            all_data.extend(page_data)

            save_checkpoint(page_number, 0, all_data, current_Chapter, current_Paragraph, current_Verse, current_Sentence)

            time.sleep(2)

        combined_data = combine_entries_hierarchical(all_data)

        final_data = {
            "metadata": metadata,
            "main_text": combined_data
        }

        with open('data.json', 'w', encoding='utf-8') as json_file:
            json.dump(final_data, json_file, ensure_ascii=False, indent=4)

        print(json.dumps(final_data, indent=4))
        print("All data extracted and saved to 'data.json'")

    except Exception as e:
        print(f"An error occurred: {e}")
        print(driver.page_source)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
