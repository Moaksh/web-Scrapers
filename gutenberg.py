import requests
from bs4 import BeautifulSoup
import json
import os
import time

base_url = "https://www.gutenberg.org/ebooks/bookshelf/"
temp_url = "https://www.gutenberg.org"

print("Scraping started...")

response = requests.get(base_url)
soup = BeautifulSoup(response.content, 'html.parser')

bookshelves = {}
for link in soup.select(".bookshelf_pages a"):
    bookshelves[link.text] = {"name": link.text, "url": temp_url + link.get('href')}

print("Bookshelves found:", len(bookshelves), "bookshelves scraped")

if os.path.exists('data.json'):
    with open('data.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"bookshelves": []}
else:
    data = {"bookshelves": []}

if os.path.exists('checkpoint.json'):
    with open('checkpoint.json', 'r') as f:
        try:
            checkpoint_data = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON data in checkpoint.json. Initializing with default values.")
            checkpoint_data = {"bookshelves_processed": [], "current_bookshelf": None, "current_book": None, "books_processed": []}
else:
    checkpoint_data = {"bookshelves_processed": [], "current_bookshelf": None, "current_book": None, "books_processed": []}

for bookshelf in bookshelves:
    if bookshelf in checkpoint_data["bookshelves_processed"]:
        continue
    checkpoint_data["current_bookshelf"] = bookshelf
    with open('checkpoint.json', 'w') as f:
        json.dump(checkpoint_data, f, indent=4)

    while True:
        try:
            response = requests.get(bookshelves[bookshelf]["url"])
            break
        except requests.exceptions.ConnectionError:
            print("Connection error. Retrying...")
            time.sleep(1)

    soup = BeautifulSoup(response.content, 'html.parser')

    books = {}
    for link in soup.select("li:nth-of-type(n+8) a.link"):
        x = link.text.split("\n")
        books[x[5]] = {"title": x[5], "url": temp_url + link.get('href')}

    print("Books found on bookshelf:", len(books), "books scraped from ", bookshelf)

    next_page = soup.select("span:nth-of-type(1) a[title='Go to the next page of results.']")

    while next_page:
        next_page_url = temp_url + next_page[0].get('href')
        while True:
            try:
                response = requests.get(next_page_url)
                break
            except requests.exceptions.ConnectionError:
                print("Connection error. Retrying...")
                time.sleep(1)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.select("li:nth-of-type(n+8) a.link"):
            x = link.text.split("\n")
            books[x[5]] = {"title": x[5], "url": temp_url + link.get('href')}
        next_page = soup.select("span:nth-of-type(1) a[title='Go to the next page of results.']")

    print("Total books found:", len(books), "books scraped from ", bookshelf)

    new_bookshelf = {"name": bookshelves[bookshelf]["name"], "url": bookshelves[bookshelf]["url"], "books": []}
    data["bookshelves"].append(new_bookshelf)
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

    for book in books:
        if book in checkpoint_data.get("books_processed", []):
            continue
        checkpoint_data["current_book"] = book
        with open('checkpoint.json', 'w') as f:
            json.dump(checkpoint_data, f, indent=4)

        while True:
            try:
                response = requests.get(books[book]["url"])
                break
            except requests.exceptions.ConnectionError:
                print("Connection error. Retrying...")
                time.sleep(1)

        soup = BeautifulSoup(response.content, 'html.parser')

        book_data = {}
        for th, td in zip(soup.select(".bibrec th"), soup.select(".bibrec td")):
            book_data[th.text.replace("\n", "")] = td.text.replace("\n", "")

        print("Book data extracted for", book, "with", len(book_data), "items")

        chapters = {}
        chapter_num = 1
        for a in soup.select("a[type='text/html']"):
            chapter_url = temp_url + a.get('href')
            while True:
                try:
                    response = requests.get(chapter_url)
                    break
                except requests.exceptions.ConnectionError:
                    print("Connection error. Retrying...")
                    time.sleep(1)
            soup = BeautifulSoup(response.content, 'html.parser')
            chapter_text = []
            try:
                for chapter in soup.select("body"):
                    chapter_text.append(chapter.get_text())
            except:
                chapter_text=[]

            chapters["url"] = chapter_url
            chapters["text"] = chapter_text

        print("Chapter bodies extracted for", book, "with", len(chapters), "chapters")

        new_book = {"title": books[book]["title"], "url": books[book]["url"], "data": book_data, "chapters": chapters}
        data["bookshelves"][-1]["books"].append(new_book)
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4)

        checkpoint_data["books_processed"] = checkpoint_data.get("books_processed", []) + [book]
        with open('checkpoint.json', 'w') as f:
            json.dump(checkpoint_data, f, indent=4)

    checkpoint_data["bookshelves_processed"] += [bookshelf]
    with open('checkpoint.json', 'w') as f:
        json.dump(checkpoint_data, f, indent=4)

with open('data.json', 'w') as f:
    json.dump(data, f, indent=4)
