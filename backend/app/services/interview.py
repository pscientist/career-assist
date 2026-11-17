import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models.db import ROOT

EXCERPT = 800

QUESTIONS = [
    "Tell me about yourself.",
    "Why are you looking for a new role?",
    "What kind of role are you looking for next?",
    "Walk me through your recent experience.",
    "Why are you interested in this company?",
    "What are your salary expectations?",
    "When could you start?",
    "Are you open to hybrid, remote, or relocation?",
    "Do you have the right to work here?",
    "What are you strongest at?",
    "Tell me about a time you handled a difficult problem at work.",
    "Why should we move you forward?",
    "Do you have any questions for me?",
]


def interview_reply(job, messages):
    user_turns = [
        message
        for message in messages
        if message.get("role") == "user" and (message.get("content") or "").strip()
    ]
    excerpt = " ".join((job.get("requirements") or "").split())[:EXCERPT]
    lines = [
        "You are a recruiter in a first conversation.",
        "Use the job details below. Do not invent facts about the candidate.",
        f"Role: {job.get('title') or ''}",
        f"Company: {job.get('company') or ''}",
    ]
    if excerpt:
        lines.append(f"Requirements: {excerpt}")
    next_index = len(user_turns)
    if next_index >= len(QUESTIONS):
        lines.append(
            "The candidate has answered every question. Thank them in one or two sentences. Do not ask another question."
        )
    else:
        lines.append(
            "React to the candidate's latest answer in one or two sentences. Then ask this question in these exact words:"
        )
        lines.append(QUESTIONS[next_index])
    lines.append("Transcript:")
    for message in messages:
        role = "Candidate" if message.get("role") == "user" else "Interviewer"
        content = (message.get("content") or "").strip()[:2000]
        if content:
            lines.append(f"{role}: {content}")
    load_dotenv(ROOT / ".env")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "\n".join(lines)}],
        temperature=0.3,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("The model returned an empty reply.")
    return text
