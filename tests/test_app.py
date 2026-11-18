from fastapi.testclient import TestClient
from app import app, USSD_SESSIONS, IVR_SESSIONS

client = TestClient(app)


def setup_function():
    USSD_SESSIONS.clear()
    IVR_SESSIONS.clear()


def start_lesson():
    client.post('/ussd', json={'session_id': 's1', 'phone_number': '+250788000001', 'text': ''})
    client.post('/ussd', json={'session_id': 's1', 'phone_number': '+250788000001', 'text': '1'})
    client.post('/ussd', json={'session_id': 's1', 'phone_number': '+250788000001', 'text': '1*1'})
    response = client.post('/ussd', json={'session_id': 's1', 'phone_number': '+250788000001', 'text': '1*1*1'})
    assert response.status_code == 200
    return response.json()['ivr_session_id']


def test_main_menu_and_course_navigation():
    r = client.post('/ussd', json={'session_id': 's1', 'text': ''})
    assert '1. Iga imboga' in r.json()['response']
    r = client.post('/ussd', json={'session_id': 's1', 'text': '1*1'})
    assert "Intangiriro ku buhinzi bw'inyanya" in r.json()['response']


def test_selecting_lesson_starts_ivr_demo_session():
    ivr_id = start_lesson()
    r = client.get(f'/ivr/{ivr_id}')
    assert r.status_code == 200
    assert r.json()['state'] == 'playing'
    assert 'Murakaza neza' in r.json()['lesson_script']


def test_press_8_then_question_returns_grounded_answer():
    ivr_id = start_lesson()
    r = client.post(f'/ivr/{ivr_id}/key/8')
    assert r.json()['state'] == 'question'
    r = client.post(f'/ivr/{ivr_id}/question', json={'transcript': 'Ni gute nahitamo imbuto?'})
    assert r.status_code == 200
    assert r.json()['grounded'] is True
    assert 'imbuto zizewe' in r.json()['answer']


def test_unknown_question_uses_safe_fallback():
    ivr_id = start_lesson()
    client.post(f'/ivr/{ivr_id}/key/8')
    r = client.post(f'/ivr/{ivr_id}/question', json={'transcript': 'Ikibazo kitari muri somo'})
    assert 'sinabonye igisubizo' in r.json()['answer']
    assert r.json()['source'] == 'fallback'


def test_press_9_starts_assessment_and_scores_answer():
    ivr_id = start_lesson()
    r = client.post(f'/ivr/{ivr_id}/key/9')
    assert r.json()['state'] == 'assessment'
    r = client.post(f'/ivr/{ivr_id}/assessment/answer', json={'answer': '1'})
    assert r.status_code == 200
    assert r.json()['correct'] is True
    assert r.json()['score'] == 1


def test_press_0_repeats_lesson_and_hash_ends_call():
    ivr_id = start_lesson()
    r = client.post(f'/ivr/{ivr_id}/key/0')
    assert r.json()['state'] == 'playing'
    r = client.post(f'/ivr/{ivr_id}/key/%23')
    assert r.json()['state'] == 'ended'
