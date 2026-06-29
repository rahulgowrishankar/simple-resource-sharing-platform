import os
import chromadb
from google.generativeai import embedding

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma_client.get_or_create_collection(name="college_resources")

def get_embedding(text):
    response = embedding.embed_content(
        model="models/gemini-embedding-001",  # Active production model string
        content=text,
        task_type="retrieval_document"
    )
    return response['embedding']

def store_chunks(resource_id, chunks):
    if not chunks:
        return
        
    ids = [f"res_{resource_id}_chunk_{i}" for i in range(len(chunks))]
    embeddings = [get_embedding(chunk) for chunk in chunks]
    metadatas = [{"resource_id": resource_id} for _ in chunks]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

def search_similar_chunks(query_text, n_results=5):
    if collection.count() == 0:
        return []
        
    query_emb = embedding.embed_content(
        model="models/gemini-embedding-001",  # Active production model string
        content=query_text,
        task_type="retrieval_query"
    )['embedding']
    
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=n_results
    )
    return results['documents'][0] if results['documents'] else []