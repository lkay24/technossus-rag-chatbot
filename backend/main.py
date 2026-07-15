import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("technossus")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about Technossus, "
    "an enterprise IT consulting company. Only use the context provided "
    "below to answer. If the answer isn't in the context, say you don't "
    "have that information on the Technossus website."
)

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def chat(request: ChatRequest):
    query_embedding = embedding_model.encode([request.question]).tolist()

    question_lower = request.question.lower()
    category_keywords = {
        "services": ["service", "offer", "provide", "solution"],
        "industries": ["industry", "industries", "sector", "vertical"],
        "careers": ["career", "job", "hiring", "position"],
    }

    boost_category = None
    for category, keywords in category_keywords.items():
        if any(kw in question_lower for kw in keywords):
            boost_category = category
            break

    general_results = collection.query(query_embeddings=query_embedding, n_results=6)
    combined = list(zip(
        general_results["documents"][0],
        [m["source"] for m in general_results["metadatas"][0]]
    ))

    if boost_category:
        category_results = collection.query(
            query_embeddings=query_embedding,
            n_results=8,
            where={"page_type": boost_category}
        )
        category_chunks = list(zip(
            category_results["documents"][0],
            [m["source"] for m in category_results["metadatas"][0]]
        ))
        combined = category_chunks + combined

    seen = set()
    deduped = []
    for chunk, source in combined:
        if chunk not in seen:
            seen.add(chunk)
            deduped.append((chunk, source))

    top_chunks = deduped[:8]
    context = "\n\n---\n\n".join(c[0] for c in top_chunks)
    sources = list(dict.fromkeys(c[1] for c in top_chunks))

    user_prompt = f"Context:\n{context}\n\nQuestion: {request.question}"

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )

    return {"answer": completion.choices[0].message.content, "sources": sources}