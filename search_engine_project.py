start_url = 'https://vm009.rz.uos.de/crawl/index.html'
base_url = 'https://vm009.rz.uos.de'


from flask import Flask, request, render_template
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def crawl(start_url, base_url, visited=None):
    if visited is None:
        visited = set()

    if start_url in visited:
        return visited

    try:
        response = requests.get(start_url)
        if 'text/html' not in response.headers['Content-Type']:
            return visited
        visited.add(start_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            url = urljoin(start_url, link['href'])
            if url.startswith(base_url) and url not in visited:
                visited.update(crawl(url, base_url, visited))
    except requests.RequestException:
        pass

    return visited

def build_index(visited_urls, index_dir):
    schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT)
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    ix = create_in(index_dir, schema)
    writer = ix.writer()

    for url in visited_urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else url
            content = soup.get_text(" ")
            writer.add_document(title=title, path=url, content=content)
        except requests.RequestException:
            continue

    writer.commit()

app = Flask(__name__)
INDEX_DIR = "indexdir"

def search_index(query_str):
    ix = create_in(INDEX_DIR, Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT))
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(query_str)
        results = searcher.search(query)
        return [(result['title'], result['path']) for result in results]

@app.route('/')
def home():
    return '''<form action="/search" method="get"> 
                <input type="text" name="q" placeholder="Enter search terms">
                <input type="submit" value="Search">
              </form>'''

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = search_index(query)
    output = "<h2>Search Results:</h2><ul>"
    for title, path in results:
        output += f'<li><a href="{path}" target="_blank">{title}</a></li>'
    output += "</ul>"
    return output

if __name__ == '__main__':
    start_url = 'https://vm009.rz.uos.de/crawl/index.html'
    base_url = 'https://vm009.rz.uos.de'
    visited_urls = crawl(start_url, base_url)
    build_index(visited_urls, INDEX_DIR)
    app.run(debug=True)
