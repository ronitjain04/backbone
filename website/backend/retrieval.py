"""Retrieve from explicit JSONL documents; never unpickle externally supplied files."""
import json
import math
import re
import base64
import gzip
import io
from collections import Counter
from pathlib import Path

STOP = set('what which where when how does do is are a an the of to and in for with explain me about can you it from'.split())
def words(text): return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in STOP and len(w)>2]

CORPUS_LIMIT = 20 * 1024 * 1024

def decode_corpus(raw, compressed=False):
    if len(raw) > CORPUS_LIMIT:
        raise ValueError('Course corpus is too large')
    if compressed:
        compressed_bytes = base64.b64decode(raw.strip(), validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_bytes)) as stream:
            raw = stream.read(CORPUS_LIMIT + 1)
        if len(raw) > CORPUS_LIMIT:
            raise ValueError('Expanded course corpus is too large')
    return raw.decode('utf-8')

def read_corpus(path):
    path = Path(path)
    if path.stat().st_size > CORPUS_LIMIT:
        raise ValueError('Course corpus is too large')
    return decode_corpus(path.read_bytes(), path.name.endswith('.jsonl.gz.b64'))

class Retriever:
    def __init__(self, path=None, mode='lexical', model_name='sentence-transformers/all-MiniLM-L6-v2', *, text=None):
        self.chunks = []
        for line in (text if text is not None else read_corpus(path)).splitlines():
            if not line.strip(): continue
            c=json.loads(line)
            if not all(isinstance(c.get(k),str) and c[k].strip() for k in ['text','source']): raise ValueError('Invalid corpus document')
            if len(c['text']) > 10000: raise ValueError('Split corpus entries into smaller chunks')
            self.chunks.append({'text':c['text'],'source':c['source'],'details':str(c.get('details',''))})
        if not self.chunks: raise ValueError('Empty corpus')
        self.mode=mode
        self.tokens=[Counter(words(c['text']+' '+c['details'])) for c in self.chunks]
        if mode=='semantic':
            import faiss
            from sentence_transformers import SentenceTransformer
            self.encoder=SentenceTransformer(model_name)
            vectors=self.encoder.encode([c['text'] for c in self.chunks],normalize_embeddings=True,convert_to_numpy=True)
            self.index=faiss.IndexFlatIP(vectors.shape[1]); self.index.add(vectors)
        elif mode!='lexical': raise ValueError('Unknown retrieval mode')

    def search(self, query):
        tokens=set(words(query))
        if not tokens: return []
        if self.mode=='semantic':
            vec=self.encoder.encode([query],normalize_embeddings=True,convert_to_numpy=True)
            scores,ids=self.index.search(vec,min(4,len(self.chunks)))
            return [self.chunks[int(i)] for s,i in zip(scores[0],ids[0]) if i>=0 and s>=0.3]
        ranked=[]
        for i,doc in enumerate(self.tokens):
            score=sum((1+math.log(doc[t]))*math.log(1+len(self.tokens)/(1+sum(t in d for d in self.tokens))) for t in tokens if doc[t])
            if score>0: ranked.append((score,i))
        ranked.sort(reverse=True)
        return [self.chunks[i] for _,i in ranked[:4]]
