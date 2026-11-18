from __future__ import annotations

from typing import Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="MenyaMuhinzi Basic-Phone Prototype",
    description="A local USSD + IVR learning-flow simulator. No telecom connection is required.",
    version="0.1.0",
)

# Demo lessons are illustrative and must be reviewed by a qualified agronomist
# before they are used to teach farmers in a live service.
COURSES = {
    "1": {
        "name": "Inyanya (Tomatoes)",
        "lessons": {
            "1": {
                "title": "Intangiriro ku buhinzi bw'inyanya",
                "script": (
                    "Murakaza neza. Iri somo riravuga ku ntangiriro y'ubuhinzi bw'inyanya. "
                    "Mbere yo gutera, hitamo imbuto nziza kandi umenye niba ubwoko bwazo "
                    "bukwiranye n'akarere kawe. Tegura umurima ufite amazi adahagarara. "
                    "Baza umukozi ushinzwe ubuhinzi mu karere kawe ku nama zijyanye n'igihe "
                    "cyo gutera n'ubwoko bw'inyanya bukwiye."
                ),
                "faq": {
                    "imbuto": "Hitamo imbuto zizewe kandi zemewe. Reba ko ubwoko bwazo bukwiranye n'akarere kawe.",
                    "umurima": "Hitamo umurima ufite ubutaka butohagiye kandi amazi ashobora gutemberamo neza.",
                    "amazi": "Amazi akenewe bitewe n'ubutaka, ikirere n'icyiciro cy'igihingwa. Kurikiza inama z'umukozi w'ubuhinzi wo mu karere kawe.",
                },
                "quiz": {
                    "question": "Mbere yo gutera inyanya, ni ikihe kintu cy'ingenzi ugomba kugenzura ku mbuto?",
                    "options": {"1": "Niba ari imbuto zizewe kandi zikwiranye n'akarere", "2": "Ibara ry'ipaki gusa"},
                    "answer": "1",
                    "explanation": "Ni ngombwa guhitamo imbuto zizewe kandi zikwiranye n'akarere kawe.",
                },
            },
            "2": {
                "title": "Gutegura pepiniyeri",
                "script": (
                    "Iri somo riravuga kuri pepiniyeri y'inyanya. Koresha ahantu hasukuye kandi "
                    "hafite amazi ashobora gutembera. Kurikirana ingemwe buri gihe kandi ushake "
                    "inama z'umukozi w'ubuhinzi ku buryo bukwiye bwo kuzitaho mu karere kawe."
                ),
                "faq": {},
                "quiz": {
                    "question": "Ni hehe hakwiye gutegurirwa pepiniyeri?",
                    "options": {"1": "Ahantu hasukuye kandi amazi ashobora gutembera", "2": "Ahantu amazi ahora ahagaze"},
                    "answer": "1",
                    "explanation": "Ahantu hasukuye kandi amazi atajya ahagarara hafasha kurinda ibibazo bya pepiniyeri.",
                },
            },
        },
    },
    "2": {"name": "Karoti (Carrots)", "lessons": {}},
    "3": {"name": "Amashu (Cabbages)", "lessons": {}},
}

USSD_SESSIONS: Dict[str, dict] = {}
IVR_SESSIONS: Dict[str, dict] = {}


class USSDRequest(BaseModel):
    session_id: str = Field(min_length=1)
    phone_number: str = Field(default="+250700000000")
    text: str = ""  # Cumulative USSD input, e.g. "1*1*1".


class QuestionRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=500)


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10)


def main_menu() -> str:
    return "Murakaza neza kuri MenyaMuhinzi\n1. Iga imboga\n2. Reba aho ugeze\n3. Ururimi"


def handle_ussd(req: USSDRequest) -> dict:
    parts = req.text.split("*") if req.text else []
    if not parts:
        USSD_SESSIONS[req.session_id] = {"phone": req.phone_number}
        return {"response": main_menu(), "action": "continue"}

    if parts[0] == "1" and len(parts) == 1:
        return {"response": "Hitamo igihingwa:\n1. Inyanya\n2. Karoti\n3. Amashu", "action": "continue"}

    if parts[0] == "1" and len(parts) == 2 and parts[1] in COURSES:
        course = COURSES[parts[1]]
        if not course["lessons"]:
            return {"response": "Amasomo y'iki gihingwa aracyategurwa. Ongera ugerageze nyuma.", "action": "end"}
        lines = [f"Amasomo ya {course['name']}:"]
        lines.extend(f"{key}. {lesson['title']}" for key, lesson in course["lessons"].items())
        return {"response": "\n".join(lines), "action": "continue"}

    if parts[0] == "1" and len(parts) == 3 and parts[1] in COURSES:
        course = COURSES[parts[1]]
        lesson = course["lessons"].get(parts[2])
        if not lesson:
            return {"response": "Iri somo ntiriboneka. Ongera ugerageze.", "action": "end"}
        ivr_id = str(uuid4())
        IVR_SESSIONS[ivr_id] = {
            "phone": req.phone_number,
            "course_id": parts[1],
            "lesson_id": parts[2],
            "state": "playing",
            "progress": 0,
            "quiz_done": False,
        }
        USSD_SESSIONS[req.session_id] = {"phone": req.phone_number, "last_ivr": ivr_id}
        return {
            "response": "Urakoze. Urahabwa telefoni igufasha kumva isomo mu Kinyarwanda.",
            "action": "start_ivr_demo",
            "ivr_session_id": ivr_id,
            "lesson_title": lesson["title"],
            "note": "Local demo only: no real telephone call is placed.",
        }

    if parts[0] == "2":
        return {"response": "Amasomo watangiye: 0\nAmasomo warangije: 0", "action": "end"}
    if parts[0] == "3":
        return {"response": "Ururimi rwatoranyijwe: Ikinyarwanda", "action": "end"}
    return {"response": "Ibyo wahisemo ntibyumvikanye. Ongera utangire.\n" + main_menu(), "action": "continue"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "menyamuhinzi-basic-phone-prototype"}


@app.get("/courses")
def list_courses():
    return [
        {"id": key, "name": value["name"], "lesson_count": len(value["lessons"])}
        for key, value in COURSES.items()
    ]


@app.post("/ussd")
def ussd(req: USSDRequest):
    return handle_ussd(req)


@app.get("/ivr/{session_id}")
def get_ivr_session(session_id: str):
    session = IVR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="IVR session not found")
    lesson = COURSES[session["course_id"]]["lessons"][session["lesson_id"]]
    return {
        "session_id": session_id,
        "state": session["state"],
        "lesson_title": lesson["title"],
        "lesson_script": lesson["script"],
        "controls": {"8": "pause and ask a question", "9": "start optional assessment", "0": "repeat lesson"},
        "notice": "The script is shown for testing. A real IVR call and Kinyarwanda audio recording/TTS are not connected yet.",
    }


@app.post("/ivr/{session_id}/key/{key}")
def ivr_key(session_id: str, key: str):
    session = IVR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="IVR session not found")
    lesson = COURSES[session["course_id"]]["lessons"][session["lesson_id"]]
    if key == "8":
        session["state"] = "question"
        return {"state": "question", "prompt": "Vuga ikibazo cyawe. Mu kizamini, andika amagambo y'ikibazo hano."}
    if key == "9":
        session["state"] = "assessment"
        quiz = lesson.get("quiz")
        if not quiz:
            return {"state": "assessment", "message": "Nta kibazo cy'isuzuma kirategurwa kuri iri somo."}
        return {"state": "assessment", **quiz}
    if key == "0":
        session["state"] = "playing"
        return {"state": "playing", "message": "Isomo risubiwemo kuva ku ntangiriro.", "lesson_script": lesson["script"]}
    if key == "#":
        session["state"] = "ended"
        return {"state": "ended", "message": "Murakoze kwiga kuri MenyaMuhinzi."}
    return {"state": session["state"], "message": "Urufunguzo ntiruzwi. Koresha 8, 9, 0 cyangwa #."}


def answer_from_lesson(lesson: dict, transcript: str) -> dict:
    q = transcript.lower()
    for keyword, answer in lesson.get("faq", {}).items():
        if keyword in q:
            return {"answer": answer, "source": "approved_demo_lesson_faq", "grounded": True}
    return {
        "answer": "Mbabarira, sinabonye igisubizo muri iri somo. Baza umukozi w'ubuhinzi cyangwa umufashamyumvire.",
        "source": "fallback",
        "grounded": True,
    }


@app.post("/ivr/{session_id}/question")
def ivr_question(session_id: str, req: QuestionRequest):
    session = IVR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="IVR session not found")
    if session["state"] != "question":
        raise HTTPException(status_code=409, detail="Press 8 before asking a question")
    lesson = COURSES[session["course_id"]]["lessons"][session["lesson_id"]]
    result = answer_from_lesson(lesson, req.transcript)
    session["state"] = "playing"
    return {**result, "state": "playing", "notice": "Question transcript is typed for this prototype; speech recognition and spoken AI audio are not connected."}


@app.post("/ivr/{session_id}/assessment/answer")
def assessment_answer(session_id: str, req: AnswerRequest):
    session = IVR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="IVR session not found")
    if session["state"] != "assessment":
        raise HTTPException(status_code=409, detail="Press 9 to start the assessment")
    lesson = COURSES[session["course_id"]]["lessons"][session["lesson_id"]]
    quiz = lesson.get("quiz")
    if not quiz:
        raise HTTPException(status_code=404, detail="No assessment available")
    correct = req.answer == quiz["answer"]
    session["quiz_done"] = True
    session["state"] = "playing"
    return {
        "correct": correct,
        "feedback": quiz["explanation"],
        "state": "playing",
        "score": 1 if correct else 0,
        "maximum_score": 1,
    }
