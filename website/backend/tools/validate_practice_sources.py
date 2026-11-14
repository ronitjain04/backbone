"""python -m website.backend.tools.validate_practice_sources PRIVATE_CORPUS.jsonl"""
import sys
from website.backend.retrieval import Retriever
from website.backend.practice.bank import load_bank, verify_sources

if __name__ == '__main__':
    bank=load_bank()
    errors=verify_sources(list(bank.values()),Retriever(sys.argv[1]).chunks)
    for error in errors: print(error)
    print(f'{len(bank)} exercises; {sum(len(e["references"]) for e in bank.values())} source anchors; {len(errors)} invalid references')
    raise SystemExit(bool(errors))
