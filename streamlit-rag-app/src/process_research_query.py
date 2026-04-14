import logging
import os

import dspy
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
import fitz
import requests
import springernature_api_client.openaccess as openaccess
from lxml import html
import feedparser
from urllib.parse import quote
from text_and_embed_pdf import extract_pdf, create_semantic_chunks, fetch_texts_from_chunks, extract_chunk_map, embed_chunks, store_embeddings_to_faiss

logger = logging.getLogger(__name__)

LOCAL_SERVER_OLLAMA = os.getenv('LOCAL_OLLAMA_SERVER')
OLLAMA_PUBLIC_KEY = os.getenv('OLLAMA_PUBLIC_KEY')

query = "In all of these files give me information about what clinicians, healthcare providers, doctors tell patients. How they tell it to patients. What the effect is. Why they need to tell the information to patients. Give me quotes."

class ExpandQuerySignature(dspy.Signature):
    """I want you to create a contextual prompt which can be used to retrieve relevant information from a knowledge base. Expand the user query to be more descriptive and detailed so that RAG Retrieval is more accurate."""
    query = dspy.InputField()
    new_contextual_prompt: str = dspy.OutputField(desc="A contextual prompt which can be used to retrieve relevant information from a knowledge base. Give more details about the topics and subtopics mentioned in the query. Make it more descriptive and detailed so that RAG Retrieval is more accurate.")


lm = dspy.LM(
        'ollama_chat/deepseek-r1:1.5b', 
        api_base=LOCAL_SERVER_OLLAMA, 
        api_key=OLLAMA_PUBLIC_KEY,
        cache=False
        )
dspy.configure(lm=lm)

def search_faiss(query, model, index, chunk_map, top_k=5):
    query_vec = model.encode([query])
    D, I = index.search(np.array(query_vec), k=top_k)
    results = [chunk_map[i] for i in I[0]]
    return results

def rag_llm_call(query: str):
    pdf_folder = Path("../research_pdfs")
    all_pdfs = list(pdf_folder.glob("*.pdf"))

    predictor = dspy.ChainOfThought(ExpandQuerySignature)
    result = predictor(
        query=query
    )
    logger.info("Expanded query: %s", result.new_contextual_prompt)

    query = result.new_contextual_prompt

    results_map = {}
    for pdf_file in all_pdfs:
        pdf_file_name = pdf_file.name
        logger.info("Paper: %s", pdf_file_name)
        index = faiss.read_index(f"../../data_source_processing/riya_research_version/data_sources/faiss_{pdf_file_name}_index.index")

        # Load ID → text mapping

        with open(f"../../data_source_processing/riya_research_version/data_sources/chunk_{pdf_file_name}_map.pkl", "rb") as f:
            chunk_map = pickle.load(f)

        rag_results = search_faiss(query=query, model=SentenceTransformer("all-MiniLM-L6-v2"), index=index, chunk_map=chunk_map)
        results_map[pdf_file_name] = rag_results
        logger.info("RAG Results for %s: %d chunks", pdf_file_name, len(rag_results))

    return results_map


def highlight_first_four_words(pdf_path, quote, output_path):
    doc = fitz.open(pdf_path)
    first_four = " ".join(quote.split()[:4])
    for page in doc:
        text_instances = page.search_for(first_four)
        for inst in text_instances:
            highlight = page.add_highlight_annot(inst)
            highlight.update()
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


# class RelatedPapersSignature(dspy.Signature):
#     """I want you to find research papers related to the given query. provide a list of research papers related to the query. """
#     query = dspy.InputField()
#     related_research_papers: list[str] = dspy.OutputField(desc="A list of actual research papers related to the query.")

class RelatedPapersSignature(dspy.Signature):
    """
    Find research papers related to the given query.
    Return a list of dictionaries, each with 'paper_name', 'link', and 'author'.
    """
    query = dspy.InputField()
    related_research_papers: list[dict] = dspy.OutputField(
        desc=(
            "A list of dictionaries, each with keys: "
            "'paper_name' (str), 'link' (str), and 'author' (str). "
            "Example: [{'paper_name': 'Paper Title', 'link': 'https://...', 'author': 'Author Name'}]"
        )
    )

def get_related_papers(query):

    predictor = dspy.ChainOfThought(RelatedPapersSignature)
    result = predictor(
        query=query
    )
    return result.related_research_papers

def search_semantic_scholar(query, limit=5):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,url"
    }
    response = requests.get(url, params=params)
    data = response.json()
    logger.info("Semantic Scholar results: %d papers", len(data.get("data", [])))
    papers = []
    for paper in data.get("data", []):
        papers.append({
            "paper_name": paper.get("title"),
            "link": paper.get("url"),
            "author": ", ".join([a["name"] for a in paper.get("authors", [])])
        })
    return papers

SPRINGER_API_KEY = os.getenv("SPRINGER_API_KEY")
openaccess_client = openaccess.OpenAccessAPI(api_key=SPRINGER_API_KEY)

def search_spring_nature(query, limit=1):
    response = openaccess_client.search(q=query, p=limit, s=1, fetch_all=False, is_premium=False)
    papers = []
    for record in response.get('records', []):
        title = record.get('title', 'No title')
        authors = record.get('creators', [])
        author_names = ", ".join([author.get('creator', 'Unknown') for author in authors])
        link = record.get('url', 'No URL')[0]['value']
        papers.append({
            "paper_name": title,
            "link": link,
            "author": author_names
        })
    return papers


def search_arxiv(query, max_results=5):
    base_url = "http://export.arxiv.org/api/query?"
    search_query = f"search_query=all:{quote(query)}&start=0&max_results={max_results}"
    feed = feedparser.parse(base_url + search_query)
    papers = []
    for entry in feed.entries:
        papers.append({
            "title": entry.title,
            "authors": ", ".join([author.name for author in entry.authors]),
            "pdf_url": next((l.href for l in entry.links if l.type == "application/pdf"), None)
        })
    return papers

def download_pdf(url, title):
    output_folder = "downloaded_pdfs"
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, title)

    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        logger.info("Downloaded to %s", output_path)
    else:
        logger.warning("Failed to download PDF from %s (status %d)", url, response.status_code)


def delete_pdf(name):
    file_path = f"downloaded_pdfs/{name}"
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info("%s deleted.", file_path)
    else:
        logger.warning("%s does not exist.", file_path)


def process_extra_papers(query, top_k=5):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    top_k = 5

    papers = search_arxiv("conflict between patient and caregiver", max_results=5)

    results_map = {}
    link_map = {}
    for paper in papers:
        logger.info("Processing: %s", paper['title'])
        download_pdf(paper['pdf_url'], paper['title']+".pdf")
        pdf_text = extract_pdf("./downloaded_pdfs/"+paper['title']+".pdf")
        semantic_chunks = create_semantic_chunks(pdf_text)
        texts_from_chunks = fetch_texts_from_chunks(semantic_chunks)
        chunk_map = extract_chunk_map(texts_from_chunks)
        embeddings = embed_chunks(texts_from_chunks)
        index = store_embeddings_to_faiss(embeddings)
        query_vec = model.encode([query])
        D, I = index.search(np.array(query_vec), k=top_k)
        results = [chunk_map[i] for i in I[0]]
        results_map[paper['title']] = results
        link_map[paper['title']] = paper['pdf_url']
        delete_pdf(paper['title']+".pdf")
    return results_map, link_map

