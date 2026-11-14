"""Versioned original exercises. Private excerpts never belong in this file."""
import hashlib
import json
from pathlib import Path

BANK_VERSION = '2026-11-14.3'
PUBLIC_FIELDS = ('id', 'version', 'course', 'topic', 'title', 'difficulty', 'prompt', 'input_help', 'references')


def load_bank():
    records = json.loads(Path(__file__).with_name('bank.json').read_text())
    return {record['id']: record for record in records}


def public_exercise(record):
    return {key: record[key] for key in PUBLIC_FIELDS}


def fingerprint(chunk):
    return hashlib.sha256(chunk['text'].encode()).hexdigest()


def verify_sources(exercises, chunks):
    available = {(c['source'], c.get('details', ''), fingerprint(c)) for c in chunks}
    return [f"{e.get('id', 'exercise')}: {r['source']} — {r['details']}"
            for e in exercises for r in e['references']
            if (r['source'], r['details'], r['fingerprint']) not in available]
