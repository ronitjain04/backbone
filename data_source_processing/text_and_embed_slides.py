import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
from pptx import Presentation

from pathlib import Path
from utils.utils import DataSourceType, build_prompt_classification, classify_information


def extract_text_from_pptx(file_path, slide_name=""):
    prs = Presentation(file_path)
    slide_texts = []

    for i, slide in enumerate(prs.slides):
        slide_text = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_text.append(shape.text.strip())
        full_text = "\n".join(slide_text)
        if full_text:
            print("Classifying slide", slide_name)
            slide_texts.append({
                "text": full_text,
                "metadata": {
                    "source": "slides",
                    "slide_name": slide_name,
                    "slide_number": i + 1,
                    "data source type": classify_information(slide_name, model="mistral")  # Classify the slide text
                }
            })

    return slide_texts

folder = Path("../slides")
file_path = folder.glob("*.pptx")

def chunk_slide_texts(slide_texts):
    all_chunks = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    for entry in slide_texts:
        chunks = splitter.create_documents([entry["text"]])
        for chunk in chunks:
            chunk.metadata = entry["metadata"]
            all_chunks.append(chunk)
    return all_chunks

def fetch_texts_from__slides_chunks(chunks):
    texts = [chunk.page_content for chunk in chunks]
    metadata = [chunk.metadata for chunk in chunks]
    return texts, metadata

def extract_slides_chunk_map(texts, metadata):
    chunk_map = {
        i: {
            "text": texts[i],
            "metadata": metadata[i]
        }
        for i in range(len(texts))
    }

    return chunk_map


def get_all_pptx_files(folder_path):
    folder = Path(folder_path)
    return list(folder.glob("*.pptx"))