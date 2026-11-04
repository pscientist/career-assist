import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from openai import OpenAI

from app.models.db import ROOT
from app.models.jobs import get_job

HERE = Path(__file__).resolve().parent


def build_cv_prompt(job_data, master_cv):
    text = (HERE / "gen_cv_prompt.txt").read_text(encoding="utf-8")
    values = {
        "{company}": job_data["company"],
        "{title}": job_data["title"],
        "{tech_stack}": ", ".join(job_data["tech_stack"]),
        "{requirements}": job_data["requirements"],
        "{master_cv}": json.dumps(master_cv, indent=2),
    }
    # One pass, not str.format: the prompt's JSON examples use single braces,
    # and text inserted for a placeholder must not be scanned for further tokens.
    return re.sub(
        r"\{(?:company|title|tech_stack|requirements|master_cv)\}",
        lambda match: values[match.group(0)],
        text,
    )


def tailor_cv_content(job_data, master_cv):
    load_dotenv(ROOT / ".env")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = build_cv_prompt(job_data, master_cv)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw_content = (response.choices[0].message.content or "").strip()
    if raw_content.startswith("```"):
        raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
        raw_content = re.sub(r"\s*```$", "", raw_content)
    # strict=False allows a raw newline inside a string. The model does that sometimes.
    return json.loads(raw_content, strict=False)


def _as_html(value):
    if isinstance(value, Markup):
        return str(value)
    return str(escape(value))


def linkify(value):
    """Turn plain http(s) URLs into links."""
    linked = re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1">\1</a>',
        _as_html(value),
    )
    return Markup(linked)


def highlight_skills(value, terms):
    text = _as_html(value)
    for term in sorted(terms, key=len, reverse=True):
        if not term:
            continue
        text = re.sub(
            rf"(?<![\w.]){re.escape(term)}(?!\w)(?!\.\w)",
            lambda match: f"<strong>{match.group(0)}</strong>",
            text,
            flags=re.IGNORECASE,
        )
    return Markup(text)


def cv_filename(job_info):
    company = re.sub(r"[^\w.-]+", "_", job_info.get("company") or "CV").strip("_") or "CV"
    return f"CV_{company}_{job_info['id']}.html"


def render_html_cv(tailored_data, master_cv, tech_stack, output_path):
    env = Environment(loader=FileSystemLoader(HERE))
    env.filters["linkify"] = linkify
    env.filters["highlight_skills"] = lambda value: highlight_skills(value, tech_stack)
    template = env.get_template("cv_template.html")
    render_context = {
        "name": master_cv["name"],
        "contact": master_cv["contact"],
        "tailored_summary": tailored_data["tailored_summary"],
        "experiences": tailored_data["experiences"],
        "recommendations": master_cv.get("recommendations", []),
        "online_profiles": master_cv.get("online_profiles", []),
        "education": master_cv.get("education", []),
        "interests": master_cv.get("interests", ""),
    }
    output_path.write_text(template.render(render_context), encoding="utf-8")
    print(f"Successfully generated tailored CV: {output_path.name}")
    return output_path.name


def generate_cv(job_id):
    job = get_job(job_id)
    if job is None:
        raise LookupError("No job with that id.")
    # The master CV file can contain a raw newline inside a string.
    master_cv = json.loads((ROOT / "master_cv.json").read_text(encoding="utf-8"), strict=False)
    print(f"Tailoring CV for {job['title']} at {job['company']}...")
    tailored = tailor_cv_content(job, master_cv)
    return render_html_cv(
        tailored,
        master_cv,
        job.get("tech_stack") or [],
        ROOT / cv_filename(job),
    )
