import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from app.models.db import ROOT
from app.models.jobs import list_jobs

AI_TOOLS = [
    "claude code",
    "cursor",
    "codex",
    "copilot",
    "chatgpt",
    "openai",
    "anthropic",
]

LABELS = {
    "claude code": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
    "copilot": "Copilot",
    "chatgpt": "ChatGPT",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}

EXCERPT = 500


def _mentioned(job):
    blob = "\n".join([job["title"], job["requirements"], " ".join(job["tech_stack"])]).lower()
    return [tool for tool in AI_TOOLS if re.search(r"\b" + re.escape(tool) + r"\b", blob)]


def _prompt(total, matches):
    lines = [
        "You are summarising job ads for one person's job search.",
        f"There are {total} stored jobs. {len(matches)} name at least one of these tools: "
        + ", ".join(LABELS[tool] for tool in AI_TOOLS)
        + ".",
        "Ads:",
    ]
    for job, tools in matches:
        names = ", ".join(LABELS[tool] for tool in tools)
        excerpt = " ".join((job["requirements"] or "").split())[:EXCERPT]
        lines.append(f"- {job['title']} at {job['company']}. Tools named: {names}.")
        if excerpt:
            lines.append(f"  Requirements: {excerpt}")
    lines.append(
        "Write one plain-text paragraph: which tools employers name, and what they expect "
        "someone to do with them. Use only what is written above. If an excerpt is thin, "
        "say so instead of inventing duties."
    )
    return "\n".join(lines)


def analyse_ai_skills():
    jobs = list_jobs(include_deleted=True)
    matches = []
    for job in jobs:
        tools = _mentioned(job)
        if tools:
            matches.append((job, tools))
    if not matches:
        names = ", ".join(LABELS[tool] for tool in AI_TOOLS)
        return f"None of the {len(jobs)} stored jobs name {names}."

    load_dotenv(ROOT / ".env")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": _prompt(len(jobs), matches)}],
        temperature=0.3,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("The model returned an empty analysis.")
    return text
