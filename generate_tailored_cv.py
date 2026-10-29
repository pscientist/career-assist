import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from openai import OpenAI

# for Open AI KEY etc
load_dotenv()

# Initialize OpenAI client (requires OPENAI_API_KEY in .env or the environment)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# Wording lives in gen_cv_prompt.txt 
# Plug in the JD (requirements, tech stack) and the Master CV
# This will be used to match the JD req with my skills and experiences
def build_cv_prompt(job_data, master_cv):
    text = (Path(__file__).resolve().parent / "gen_cv_prompt.txt").read_text(encoding="utf-8")
    values = {
        "{company}": job_data["company"],
        "{title}": job_data["title"],
        "{tech_stack}": ", ".join(job_data["tech_stack"]),
        "{requirements}": job_data["requirements"],
        "{master_cv}": json.dumps(master_cv, indent=2),
    }
    # One-pass replace, not str.format: the prompt's JSON examples use single braces,
    # and text inserted for a placeholder must not be scanned for further tokens.
    return re.sub(
        r"\{(?:company|title|tech_stack|requirements|master_cv)\}",
        lambda match: values[match.group(0)],
        text,
    )

#    Uses LLM to generate a targeted professional summary and select/emphasize 
#    the most relevant experience bullet points matching the job posting.
def tailor_cv_content(job_data, master_cv):

    # prompt for matching my CV with JD req
    prompt = build_cv_prompt(job_data, master_cv)

    # Make a call to GPT to build custom CV
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    raw_content = response.choices[0].message.content.strip()

    # returns JSON
    return json.loads(raw_content)

# format link texts
def _as_html(value):
    if isinstance(value, Markup):
        return str(value)
    return str(escape(value))

# Create links for a tags
def linkify(value):
    """Turn plain http(s) URLs into links."""
    linked = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1">\1</a>',
        _as_html(value),
    )
    return Markup(linked)

# Bold technologies from the job tech stack, keeping the CV's spelling
def highlight_skills(value, terms):
  
    text = _as_html(value)
  
    for term in sorted(terms, key=len, reverse=True):
        if not term:
            continue
  
        text = re.sub(
            rf'(?<![\w.]){re.escape(term)}(?!\w)(?!\.\w)',
            lambda match: f'<strong>{match.group(0)}</strong>',
            text,
            flags=re.IGNORECASE,
        )
    return Markup(text)

def render_html_cv(tailored_data, master_cv, tech_stack, output_filename="tailored_cv.html"):
    env = Environment(loader=FileSystemLoader('.'))
    env.filters['linkify'] = linkify
    env.filters['highlight_skills'] = lambda value: highlight_skills(value, tech_stack)
    template = env.get_template('cv_template.html')

    # Merge contact info from master CV with tailored content
    render_context = {
        "name": master_cv["name"],
        "contact": master_cv["contact"],
        "tailored_summary": tailored_data["tailored_summary"],
        "experiences": tailored_data["experiences"],
        "recommendations": master_cv.get("recommendations", []),
        "online_profiles": master_cv.get("online_profiles", []),
        "education": master_cv.get("education", []),
        "interests": master_cv.get("interests", "")
    }

    html_output = template.render(render_context)

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"Successfully generated tailored CV: {output_filename}")
    return output_filename

def cv_filename(job_info):
    company = re.sub(r"[^\w.-]+", "_", job_info.get("company") or "CV").strip("_") or "CV"
    job_id = str(job_info.get("id") or "").strip()
    if job_id:
        return f"CV_{company}_{job_id}.html"
    return f"CV_{company}.html"

def generate_cv(job_info, master_cv_path="master_cv.json"):
    master_cv_info = load_json(master_cv_path)
    print(f"Tailoring CV for {job_info['title']} at {job_info['company']}...")
    tailored_result = tailor_cv_content(job_info, master_cv_info)
    return render_html_cv(
        tailored_result,
        master_cv_info,
        job_info.get("tech_stack") or [],
        output_filename=cv_filename(job_info),
    )

if __name__ == "__main__":
    generate_cv(load_json("phq.json"))