import pytest
from website.backend.practice.bank import load_bank
from website.backend.practice.checking import check, parse_number
from website.backend.practice.lc3 import check_program

@pytest.mark.parametrize('answer',['45','32 + 8 + 4 + 1','0x2d','0b101101','2^5+2^3+2^2+1'])
def test_accepts_equivalent_calculations(answer):
    assert check(load_bank()['num-01'],answer,'')['status']=='correct'

@pytest.mark.parametrize('answer',['__import__("os")','2**1000000','1/0','one million maybe','[45]'])
def test_uninterpretable_input_is_not_marked_wrong(answer):
    assert check(load_bank()['num-01'],answer,'')['status']=='needs_clarification'

def test_units_are_checked_and_converted():
    e=load_bank()['mem-03']
    assert check(e,'2 KiB','')['status']=='correct'
    assert check(e,'16384 bits','')['status']=='correct'
    assert check(e,'2048 bits','')['status']=='incorrect'
    assert check(e,'2048 KB','')['status']=='needs_clarification'

def test_signed_patterns_and_width_are_not_conflated():
    assert check(load_bank()['num-02'],'246','')['status']=='incorrect'
    assert check(load_bank()['num-03'],'-13','')['status']=='needs_clarification'
    assert check(load_bank()['num-03'],'0b11110011','')['status']=='correct'
    assert check(load_bank()['lc3-04'],'x2FFE','')['status']=='correct'

def test_bounded_lc3_accepts_alternative_correct_code():
    e=load_bank()['lc3-05']
    assert check(e,'AND R0,R1,#0\nADD R0,R0,#-5','')['status']=='correct'
    assert check(e,'AND R0,R0,#0\nADD R0,R0,#4\nNOT R0,R0','')['status']=='correct'
    assert check(e,'ADD R0,R0,#-5','')['status']=='incorrect'
    assert check(e,'TRAP x25','')['status']=='needs_clarification'
    assert check(e,'AND R0,R0,#0\n'+'ADD R0,R0,#0\n'*8,'')['status']=='needs_clarification'
    assert check(e,'ADD R0,R1,#16','')['status']=='needs_clarification'

def test_choice_prose_does_not_get_silently_interpreted():
    assert check(load_bank()['num-05'],'yes','')['status']=='correct'
    assert check(load_bank()['num-05'],'no','')['status']=='incorrect'
    assert check(load_bank()['num-05'],'yes but no overflow actually','')['status']=='needs_clarification'

def test_every_authored_deterministic_answer_and_follow_up_checks():
    for exercise in load_bank().values():
        for e in (exercise,exercise['follow_up']):
            if e['checker']['kind']=='explanation':continue
            assert check(e,e['answer'],'')['status']=='correct',e['id']

def test_fraction_growth_is_bounded_before_exponentiation():
    e=load_bank()['num-01']
    assert check(e,'((((1/2)^32)^32)^32)^32','')['status']=='needs_clarification'
    assert parse_number('1/8')==0.125

@pytest.mark.parametrize('answer',['0x20 + 0xD','x20 + xD','0xD+0x20'])
def test_hexadecimal_calculations_do_not_get_mistaken_for_units(answer):
    assert check(load_bank()['num-01'],answer,'')['status']=='correct'
