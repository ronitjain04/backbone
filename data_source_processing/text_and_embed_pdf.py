import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
from pptx import Presentation
import pickle

from text_and_embed_slides import extract_text_from_pptx, extract_slides_chunk_map, chunk_slide_texts, fetch_texts_from__slides_chunks

def extract_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text() + "\n"
    return text


def create_semantic_chunks(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,     # max size of each chunk (in characters)
        chunk_overlap=100    # repeated content from previous chunk to preserve context
    )

    chunks = splitter.create_documents([text])

    return chunks

def fetch_texts_from_chunks(chunks):
    texts = [chunk.page_content for chunk in chunks]
    return texts

def extract_chunk_map(texts):
    chunk_map = {
        i: {
            "text": texts[i]
        }
        for i in range(len(texts))
    }

    return chunk_map

def embed_chunks(texts_from_chunks):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(
        texts_from_chunks,
        batch_size=64,           # Tune based on your RAM/GPU
        show_progress_bar=True,
        convert_to_numpy=True    # Easier for FAISS
    )
    return embeddings

def store_embeddings_to_faiss(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index
