import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

RAW_DIR = "data/raw"
CHROMA_DIR = "chroma_db"
CHUNK_SIZE = 500
OVERLAP = 100

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current = current + "\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    final = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            tail = chunks[i-1][-overlap:]
            chunk = tail + "\n" + chunk
        final.append(chunk)

    return final

with open(os.path.join(RAW_DIR, "manifest.json"), "r", encoding="utf-8") as f:
    manifest = json.load(f)

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_DIR)
try:
    client.delete_collection("technossus")
except Exception:
    pass
collection = client.create_collection("technossus", metadata={"hnsw:space": "cosine"})

all_chunks = []
all_ids = []
all_metadatas = []

for filename, url in manifest.items():
    filepath = os.path.join(RAW_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    for idx, chunk in enumerate(chunks):
        all_chunks.append(chunk)
        all_ids.append(f"{filename}_{idx}")
        from urllib.parse import urlparse
        path_parts = urlparse(url).path.strip("/").split("/")
        page_type = path_parts[0] if path_parts and path_parts[0] else "home"
        all_metadatas.append({"source": url, "page_type": page_type})

print(f"Total chunks across all pages: {len(all_chunks)}")
print("Generating embeddings...")
embeddings = model.encode(all_chunks, show_progress_bar=True).tolist()

collection.add(
    ids=all_ids,
    embeddings=embeddings,
    documents=all_chunks,
    metadatas=all_metadatas
)

print(f"Done. Stored {collection.count()} chunks in ChromaDB.")