import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
from pptx import Presentation
import pickle
from enum import Enum

from text_and_embed_slides import extract_text_from_pptx, extract_slides_chunk_map, chunk_slide_texts, fetch_texts_from__slides_chunks, get_all_pptx_files
from text_and_embed_pdf import extract_pdf, create_semantic_chunks, fetch_texts_from_chunks, extract_chunk_map, embed_chunks, store_embeddings_to_faiss
from pathlib import Path
import requests


#pdf textbook extraction and embeddings
    
pdf_text = extract_pdf("CS2200Book.pdf")
semantic_chunks = create_semantic_chunks(pdf_text)
texts_from_chunks = fetch_texts_from_chunks(semantic_chunks)
chunk_map = extract_chunk_map(texts_from_chunks)
embeddings = embed_chunks(texts_from_chunks)
index = store_embeddings_to_faiss(embeddings)
start_index = len(embeddings)
print(start_index)

#Only slides processing
# dimension = 384
# index = faiss.IndexFlatL2(dimension)
# start_index = 0
# chunk_map = {}

pptx_files = get_all_pptx_files("../slides")



for pptx_file in pptx_files:
    print("Processing:", pptx_file)
    slide_texts = extract_text_from_pptx(str(pptx_file), slide_name=pptx_file.stem)
    slides_chunk = chunk_slide_texts(slide_texts)
    texts, metadata = fetch_texts_from__slides_chunks(slides_chunk)
    chunk_map_slides = extract_slides_chunk_map(texts, metadata)
    embeddings_slides = embed_chunks(texts)
    index.add(embeddings_slides)

    for i in range(len(texts)):
        chunk_map[start_index + i] = {
            "text": texts[i],
            "metadata": metadata[i]
        }
    start_index += len(embeddings_slides)

faiss.write_index(index, "../data_sources/faiss_index.index")
with open("../data_sources/chunk_map.pkl", "wb") as f:
    pickle.dump(chunk_map, f)
