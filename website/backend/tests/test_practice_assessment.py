import asyncio
import json
from website.backend.practice.bank import load_bank
from website.backend.practice.assessment import assess, validate_assessment

CHUNKS=[{'source':'Book','details':'p. 76','text':'Addressability is bits stored per location.'}]

def payload(status='met',evidence='Both have 4096 locations'):
    return {'criteria':[{'id':'concept','status':status,'evidence':evidence,'source_ids':[1], 'explanation':'Each address selects one location.'}], 'message':'Your distinction is supported.', 'clarification':None, 'misconceptions':[]}

class Model:
    def __init__(self,data):self.data=data
    async def assess_practice(self,content):return json.dumps(self.data)

def test_alternative_written_explanation_can_satisfy_rubric():
    e=load_bank()['mem-06'];work='Both have 4096 locations, but B stores twice the bits per location.'
    result=asyncio.run(assess(e,work,'',CHUNKS,Model(payload())))
    assert result['status']=='correct'
    assert result['criteria'][0]['status']=='met'

def test_forged_quotations_and_source_numbers_fail_closed():
    for patch in [dict(evidence='student never said this'),dict(source_ids=[99])]:
        p=payload();p['criteria'][0].update(patch)
        result=asyncio.run(assess(load_bank()['mem-06'],'Both have 4096 locations','',CHUNKS,Model(p)))
        assert result['status']=='needs_clarification'
        assert result['misconception'] is None

def test_reports_first_supported_error_by_student_span_order():
    e=load_bank()['mem-06'];work='Both have 12 locations. Each stores 12 bits.'
    data={'criteria':[{'id':'concept','status':'contradicted','evidence':'Both have 12 locations','source_ids':[1],'explanation':'Address width is not location count.'}],
          'message':'Revisit the location count.','clarification':None,'misconceptions':[
              {'label':'Wrong addressability','criterion':'concept','evidence':'Each stores 12 bits','source_ids':[1]},
              {'label':'Width used as count','criterion':'concept','evidence':'Both have 12 locations','source_ids':[1]}]}
    result=asyncio.run(assess(e,work,'',CHUNKS,Model(data)))
    assert result['status']=='incorrect'
    assert result['misconception']['evidence']=='Both have 12 locations'

def test_insufficient_evidence_asks_a_question_without_inventing_an_error():
    p=payload('unclear','');p['clarification']='What does 12 measure in your calculation?'
    result=asyncio.run(assess(load_bank()['mem-06'],'12','',CHUNKS,Model(p)))
    assert result['status']=='needs_clarification'
    assert result['clarification']
    assert result['misconception'] is None

def test_no_sources_or_malformed_model_is_unavailable():
    assert asyncio.run(assess(load_bank()['mem-06'],'same addresses','',[],Model({})))['status']=='unavailable'
    assert asyncio.run(assess(load_bank()['mem-06'],'same addresses','',CHUNKS,Model({})))['status']=='needs_clarification'

def test_first_incorrect_arithmetic_equality_is_supported_directly():
    from website.backend.practice.assessment import first_arithmetic_error
    work='32 + 8 = 40\n40 + 4 = 46\n46 + 1 = 47'
    finding=first_arithmetic_error(work)
    assert finding['evidence']=='40 + 4 = 46'
    assert first_arithmetic_error('45') is None
    assert first_arithmetic_error('2^12 = 4096\n4096 * 2 = 8192') is None
