import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models.db import ROOT

EXCERPT = 800


def summarise_company(job):
    excerpt = " ".join((job.get("requirements") or "").split())[:EXCERPT]
    stack = ", ".join(job.get("tech_stack") or [])
    lines = [
        "Write 3 to 4 plain sentences about this employer for a job applicant.",
        "Cover the company size, its industry, and what this role suggests they are hiring for.",
        "Use the job details below. You may use well-known facts about the company.",
        "If the size or industry is not in the details and is not a well-known fact, say that it is not known. Do not invent a headcount.",
        f"Company: {job.get('company') or ''}",
        f"Location: {job.get('location') or ''}",
        f"Role: {job.get('title') or ''}",
    ]
    if stack:
        lines.append(f"Tech stack: {stack}")
    if excerpt:
        lines.append(f"Requirements: {excerpt}")
    load_dotenv(ROOT / ".env")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "\n".join(lines)}],
        temperature=0.3,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("The model returned an empty summary.")
    return text
