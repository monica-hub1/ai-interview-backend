from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# ---------------- AI QUESTION ----------------
def generate_question(job_desc, history):
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Ask ONE professional FAANG interview question."},
                {"role": "user", "content": f"{job_desc}\n{history}"}
            ]
        }
    )
    return res.json()["choices"][0]["message"]["content"]

# ---------------- AVATAR ----------------
def generate_avatar(text):
    res = requests.post(
        "https://api.heygen.com/v2/video/generate",
        headers={"X-API-KEY": HEYGEN_API_KEY},
        json={
            "script": text,
            "avatar": "anna_public",  # default avatar
            "voice": "female",
            "background": "office"
        }
    )
    data = res.json()
    return data.get("data", {}).get("video_url", "")

# ---------------- EVALUATION ----------------
def evaluate(q, a):
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Score answer from 0-10 and give short feedback."},
                {"role": "user", "content": f"Q:{q}\nA:{a}"}
            ]
        }
    )
    return res.json()["choices"][0]["message"]["content"]

# ---------------- INTERVIEW ----------------
@app.websocket("/ws/interview")
async def interview(ws: WebSocket):

    await ws.accept()

    job_desc = await ws.receive_text()

    history = []
    results = []
    count = 0

    def next_q():
        return generate_question(job_desc, history)

    q = next_q()
    video = generate_avatar(q)

    await ws.send_json({
        "type": "question",
        "question": q,
        "video": video
    })

    while True:
        data = await ws.receive_json()

        ans = data["answer"]
        history.append(ans)

        results.append(evaluate(q, ans))

        count += 1

        if count >= 10:
            await ws.send_json({
                "type": "end",
                "results": results
            })
            break

        q = next_q()
        video = generate_avatar(q)

        await ws.send_json({
            "type": "question",
            "question": q,
            "video": video
        })