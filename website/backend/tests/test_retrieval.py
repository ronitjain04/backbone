import json
import pytest
from website.backend.retrieval import Retriever

@pytest.fixture
def corpus(tmp_path):
    p=tmp_path/'notes.jsonl'
    p.write_text('\n'.join(json.dumps(c) for c in [
        {'source':'Original notes','details':'Pipeline','text':'A load use data hazard may require a pipeline stall.'},
        {'source':'Original notes','details':'Memory','text':'Virtual memory maps virtual pages to physical page frames.'}]))
    return p

def test_retrieves_relevant_source_and_refuses_unrelated_question(corpus):
    r=Retriever(corpus)
    assert r.search('load hazard')[0]['details']=='Pipeline'
    assert r.search('make pasta')==[]
    assert r.search('what is it')==[]

def test_empty_or_invalid_corpus_is_not_ready(tmp_path):
    p=tmp_path/'empty.jsonl';p.write_text('')
    with pytest.raises(ValueError): Retriever(p)
    p.write_text(json.dumps({'text':'hazards'}))
    with pytest.raises(ValueError): Retriever(p)

def test_private_secret_file_loads_the_same_sources_as_plain_jsonl(corpus, tmp_path):
    import base64
    import gzip
    packed=tmp_path/'notes.jsonl.gz.b64'
    packed.write_bytes(base64.b64encode(gzip.compress(corpus.read_bytes())))
    assert Retriever(packed).search('load hazard') == Retriever(corpus).search('load hazard')
    packed.write_text('not base64')
    with pytest.raises(ValueError): Retriever(packed)
