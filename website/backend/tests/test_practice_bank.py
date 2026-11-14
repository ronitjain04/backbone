import json
from pathlib import Path
from website.backend.practice.bank import load_bank, public_exercise, verify_sources


def test_bank_complete_and_answers_not_public():
    bank=load_bank()
    assert len(bank)==18
    assert {e['topic'] for e in bank.values()}=={'numbers','memory','lc3'}
    for e in bank.values():
        assert all(e[k] for k in ['answer','reasoning','rubric','mistakes','references','follow_up'])
        assert len(e['hints'])==3
        public=public_exercise(e)
        assert not {'answer','reasoning','checker','hints','mistakes','rubric','follow_up'} & public.keys()
        assert all('fingerprint' in r and r['details'] for r in public['references'])


def test_reference_validation_detects_stale_or_missing_evidence():
    chunks=[{'source':'Book','details':'p. 1','text':'One word has sixteen bits.'}]
    import hashlib
    digest=hashlib.sha256(chunks[0]['text'].encode()).hexdigest()
    exercise={'references':[dict(chunks[0],fingerprint=digest)]}
    assert verify_sources([exercise],chunks)==[]
    chunks[0]['text']='Changed'
    assert verify_sources([exercise],chunks)
