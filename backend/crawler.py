import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
import json

BASE_URL = "https://www.technossus.com/"
DOMAIN = urlparse(BASE_URL).netloc
MAX_PAGES = 150
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")

SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js",
            ".pdf", ".zip", ".mp4", ".woff", ".woff2", ".xml", ".json")

def clean_url(url):
    parsed = urlparse(url)
    path = parsed.path
    if not path.endswith("/") and not path.lower().endswith(SKIP_EXT):
        path = path + "/"
    return parsed._replace(path=path, query="", fragment="").geturl()

def get_links(html, current_url):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        full_url = urljoin(current_url, a["href"])
        clean = clean_url(full_url)
        parsed = urlparse(clean)
        if (parsed.scheme in ("http", "https") and parsed.netloc == DOMAIN
                and "cdn-cgi" not in clean and not parsed.path.lower().endswith(SKIP_EXT)):
            links.add(clean)
    return links

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)

os.makedirs(OUTPUT_DIR, exist_ok=True)
visited = set()
queue = [clean_url(BASE_URL)]
manifest = {}

while queue and len(visited) < MAX_PAGES:
    url = queue.pop(0)
    if url in visited:
        continue

    visited.add(url)
    print(f"Visiting: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Skipped ({e})")
        continue
    if "text/html" not in response.headers.get("Content-Type", ""):
        continue

    text = extract_text(response.text)
    filename = f"page_{len(manifest)}.txt"
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(text)
    manifest[filename] = url

    new_links = get_links(response.text, url)
    for link in new_links:
        if link not in visited and link not in queue:
            queue.append(link)

    time.sleep(0.3)

with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print(f"\nTotal pages saved: {len(manifest)}")