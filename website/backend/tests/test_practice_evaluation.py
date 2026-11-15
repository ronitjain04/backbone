"""Behavioral evaluation matrix: outcomes, alternatives, ambiguity and evidence fidelity."""
import pytest
from website.backend.practice.bank import load_bank, fingerprint, verify_sources
from website.backend.practice.checking import check
from website.backend.practice.assessment import validate_assessment
from website.backend.practice.hints import make_hint
from website.backend.practice.visual import explanation

CASES=[
 ('num-01','45','correct','correct'),('num-01','32+8+4+1','correct','alternative'),
 ('num-01','46','incorrect','common mistake'),('num-01','maybe forty-ish','needs_clarification','ambiguous'),
 ('num-02','246','incorrect','common mistake'),('num-02','-10','correct','correct'),
 ('mem-03','2 KiB','correct','alternative'),('mem-03','16384 bits','correct','alternative'),
 ('mem-03','2048 bits','incorrect','common mistake'),('mem-03','2048 KB','needs_clarification','ambiguous'),
 ('lc3-04','x2FFE','correct','correct'),('lc3-05','AND R0,R1,#0\nADD R0,R0,#-5','correct','alternative'),
 ('lc3-05','ADD R0,R0,#-5','incorrect','common mistake'),('lc3-05','TRAP x25','needs_clarification','ambiguous'),
 ('num-01','__import__("os").system("id")','needs_clarification','adversarial'),
]
@pytest.mark.parametrize('eid,answer,expected,category',CASES)
def test_accuracy_matrix(eid,answer,expected,category):
    assert check(load_bank()[eid],answer,'')['status']==expected

@pytest.mark.parametrize('status,evidence,source_ids,valid',[
 ('met','Different addressability changes total capacity.',[1],True),
 ('contradicted','Same address width means same capacity.',[1],True),
 ('unclear','',[],True),('contradicted','invented student quote',[1],False),
 ('met','Different addressability changes total capacity.',[99],False)])
def test_written_rubric_evidence_and_citation_matrix(status,evidence,source_ids,valid):
    text='Different addressability changes total capacity. Same address width means same capacity.'
    data={'criteria':[{'id':'concept','status':status,'evidence':evidence,'source_ids':source_ids}], 'message':'Review the per-location quantity.','misconceptions':[]}
    if not valid:
        with pytest.raises(ValueError):validate_assessment(data,load_bank()['mem-06'],text,[{'source':'book','text':'Addressability determines the bits in a location.'}])
    else:
        result=validate_assessment(data,load_bank()['mem-06'],text,[{'source':'book','text':'Addressability determines the bits in a location.'}])
        assert result['status']=={'met':'correct','contradicted':'incorrect','unclear':'needs_clarification'}[status]


def test_all_early_hints_and_visuals_withhold_expected_answer():
    class Retriever:
        chunks=[{'source':'Fixture','details':'1','text':'Use the quantity represented by each address.'}]
        def search(self,q):return self.chunks
    r=Retriever();ref={'source':'Fixture','details':'1','fingerprint':fingerprint(r.chunks[0])}
    checked=0
    for parent in load_bank().values():
        for original in (parent,parent['follow_up']):
            e=dict(original,references=[ref]);hint=make_hint(e,1,[],r);assert hint['status']=='hint'
            # Compare complete distinctive answers; single characters are not a useful leakage detector.
            if len(e['answer'])>=4:assert e['answer'].lower() not in hint['message'].lower(),e['id']
            assert 'expected_answer' not in hint and 'answer' not in hint
            assert verify_sources([e],r.chunks)==[];checked+=1
    assert checked==36
    for eid in ('mem-03','mem-06'):
        e=load_bank()[eid]
        for stage in (1,2,3):
            r=explanation(e,stage,[],[{'source':'Fixture'}]);assert e['answer'] not in r['message'];assert 'answer' not in r
