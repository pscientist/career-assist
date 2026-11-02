import html
import json
import re
import sys
from pathlib import Path


def repair_wrapped_json(text):
    """Join editor-wrapped lines that landed inside JSON strings."""
    out = []
    in_string = False
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if in_string:
            if char == "\\":
                nxt = text[i + 1] if i + 1 < length else ""
                if nxt == "\n":
                    out.append("\\")
                    i += 2
                    while i < length and text[i] in " \t":
                        i += 1
                    continue
                out.append(char)
                if nxt:
                    out.append(nxt)
                    i += 2
                else:
                    i += 1
                continue
            if char == '"':
                in_string = False
                out.append(char)
            elif char == "\n":
                out.append(" ")
                i += 1
                while i < length and text[i] in " \t":
                    i += 1
                continue
            else:
                out.append(char)
        else:
            if char == '"':
                in_string = True
            out.append(char)
        i += 1
    return "".join(out)


def bold_tech(escaped_text, tech_stack):
    terms = sorted({term for term in tech_stack if term}, key=len, reverse=True)
    if not terms:
        return escaped_text
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b",
        re.IGNORECASE,
    )
    return pattern.sub(lambda match: f"<strong>{match.group(0)}</strong>", escaped_text)


def requirements_html(text, tech_stack):
    if not text or not text.strip():
        return '<p class="empty">No requirements captured</p>'

    paragraphs = []
    for block in re.split(r"\n\s*\n", text.strip()):
        cleaned = block.strip()
        if not cleaned:
            continue
        escaped = html.escape(cleaned)
        escaped = bold_tech(escaped, tech_stack)
        escaped = escaped.replace("\n", "<br>\n")
        paragraphs.append(f"<p>{escaped}</p>")
    return "\n".join(paragraphs) or '<p class="empty">No requirements captured</p>'


def job_seek_id(job):
    job_id = str(job.get("id") or "").strip()
    if job_id:
        return job_id
    match = re.search(r"/job/(\d+)", job.get("url") or "")
    return match.group(1) if match else ""


def load_jobs(json_path):
    source = Path(json_path)
    raw = repair_wrapped_json(source.read_text(encoding="utf-8"))
    return json.loads(raw, strict=False)


# Removals live beside the scrapes so the next scrape still hides the same Seek id.
STATUS_PATH = Path(__file__).resolve().parent / "job_status.json"


def load_job_status():
    if not STATUS_PATH.is_file():
        return {}
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def removed_job_ids():
    return {
        str(job_id)
        for job_id, entry in load_job_status().items()
        if isinstance(entry, dict) and entry.get("status") == "removed"
    }


def mark_job_removed(job_id):
    status = load_job_status()
    status[str(job_id)] = {"status": "removed"}
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def render_jobs_html(json_path):
    source = Path(json_path)
    jobs = load_jobs(source)
    output = source.with_suffix(".html")
    hidden = removed_job_ids()

    index_items = []
    sections = []
    visible_index = 0
    for job in jobs:
        job_id = job_seek_id(job)
        if job_id and job_id in hidden:
            continue
        visible_index += 1
        index = visible_index
        anchor = f"job-{index}"
        title = job.get("title") or "Untitled"
        company = job.get("company") or "Unknown company"
        location = job.get("location") or ""
        url = job.get("url") or ""
        tech_stack = job.get("tech_stack") or []

        index_items.append(
            f'<li><a href="#{anchor}">{html.escape(company)} — {html.escape(title)}</a></li>'
        )

        labels = "".join(f"<li>{html.escape(term)}</li>" for term in tech_stack)
        stack_html = f'<ul class="stack">{labels}</ul>' if labels else ""
        link_html = (
            f'<p><a href="{html.escape(url, quote=True)}">View on Seek</a></p>'
            if url
            else ""
        )
        actions_html = (
            f'''<div class="actions">
  <form method="post" action="/generate">
    <input type="hidden" name="id" value="{html.escape(job_id, quote=True)}">
    <button type="submit">Generate CV</button>
  </form>
  <form method="post" action="/remove">
    <input type="hidden" name="id" value="{html.escape(job_id, quote=True)}">
    <button type="submit">Remove</button>
  </form>
</div>'''
            if job_id
            else ""
        )
        location_html = f" · {html.escape(location)}" if location else ""
        sections.append(
            f"""<article id="{anchor}">
  <h2>{html.escape(title)}</h2>
  <p class="meta">{html.escape(company)}{location_html}</p>
  {link_html}
  {actions_html}
  {stack_html}
  {requirements_html(job.get("requirements") or "", tech_stack)}
</article>"""
        )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Scraped jobs</title>
  <style>
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px auto; max-width: 760px; background: #fff; color: #222; line-height: 1.5; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; }}
    .scrape {{ margin: 0 0 20px; }}
    .scrape form {{ margin: 0 0 4px; }}
    nav ol {{ padding-left: 20px; }}
    nav a, article a {{ color: #222; }}
    article {{ margin-top: 36px; padding-top: 12px; border-top: 2px solid #333; }}
    h2 {{ font-size: 20px; margin-bottom: 4px; }}
    .meta {{ color: #555; margin-top: 0; }}
    .stack {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 0; list-style: none; }}
    .stack li {{ border: 1px solid #ccc; border-radius: 4px; padding: 2px 8px; font-size: 13px; }}
    .empty {{ color: #666; font-style: italic; }}
    button {{ font: inherit; padding: 4px 10px; cursor: pointer; }}
    .actions {{ display: flex; gap: 8px; align-items: center; }}
    .actions form {{ margin: 0; }}
  </style>
</head>
<body>
  <h1>Scraped jobs</h1>
  <div class="scrape">
    <form method="post" action="/scrape">
      <button type="submit">Scrape Seek</button>
    </form>
    <p class="meta">One page of developer jobs in New Zealand. This takes a few minutes.</p>
  </div>
  <nav>
    <ol>
      {"".join(index_items)}
    </ol>
  </nav>
  {"".join(sections)}
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")
    return str(output)


if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not json_file:
        matches = sorted(Path(".").glob("seek_jobs_with_stack_*.json"))
        if not matches:
            raise SystemExit("No seek_jobs_with_stack_*.json file found")
        json_file = matches[-1]
    print(f"Wrote {render_jobs_html(json_file)}")
