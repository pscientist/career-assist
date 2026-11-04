import html
import json
import re
import sys
from pathlib import Path

from job_store import manual_jobs, statuses


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


def render_jobs_html(json_path):
    source = Path(json_path)
    jobs = load_jobs(source)
    scrape_ids = {job_seek_id(job) for job in jobs}
    added = [job for job in manual_jobs() if job_seek_id(job) not in scrape_ids]
    jobs = added + jobs
    output = source.with_suffix(".html")
    records = statuses()

    index_items = []
    sections = []
    visible_index = 0
    for job in jobs:
        job_id = job_seek_id(job)
        record = records.get(job_id) or {}
        if job_id and record.get("status") == "deleted":
            continue
        visible_index += 1
        index = visible_index
        anchor = f"job-{index}"
        title = job.get("title") or "Untitled"
        company = job.get("company") or "Unknown company"
        location = job.get("location") or ""
        url = job.get("url") or ""
        tech_stack = job.get("tech_stack") or []

        current = record.get("status")
        if current not in ("applied", "interviewing"):
            current = "new"
        status_text = {"new": "New", "applied": "Applied", "interviewing": "Interviewing"}[current]
        index_items.append(
            f'<tr><td><a href="#{anchor}">{html.escape(title)}</a></td><td>{status_text}</td></tr>'
        )

        labels = "".join(f"<li>{html.escape(term)}</li>" for term in tech_stack)
        stack_html = f'<ul class="stack">{labels}</ul>' if labels else ""
        link_html = (
            f'<p><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">View on Seek</a></p>'
            if url
            else ""
        )
        options = "".join(
            f'<option value="{value}"{" selected" if value == current else ""}>{label}</option>'
            for value, label in (("new", "New"), ("applied", "Applied"), ("interviewing", "Interviewing"))
        )
        actions_html = (
            f'''<div class="actions">
  <form method="post" action="/generate">
    <input type="hidden" name="id" value="{html.escape(job_id, quote=True)}">
    <button type="submit">Generate CV</button>
  </form>
  <form method="post" action="/status">
    <input type="hidden" name="id" value="{html.escape(job_id, quote=True)}">
    <select name="status" aria-label="Status" onchange="this.form.submit()">
      {options}
    </select>
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
  <title>Current Positions</title>
  <style>
    body {{ font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; margin: 40px auto; max-width: 760px; background: #f4f6f8; color: #1a2332; line-height: 1.5; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 3px solid #1d4e89; }}
    .scrape {{ margin: 16px 0 24px; }}
    .scrape-actions {{ display: flex; gap: 8px; align-items: center; margin: 0 0 6px; }}
    .scrape form {{ margin: 0; }}
    .scrape button {{ background: #1d4e89; color: #fff; border-color: #1d4e89; }}
    a.add-job {{ display: inline-block; padding: 6px 12px; background: #fff; color: #1a2332; border: 1px solid #d8dee6; border-radius: 6px; }}
    a {{ color: #1d4e89; text-decoration: none; }}
    table.positions {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee6; }}
    table.positions th, table.positions td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #d8dee6; }}
    table.positions th {{ color: #5c6b7a; font-weight: 600; }}
    table.positions tr:last-child td {{ border-bottom: none; }}
    article {{ margin-top: 20px; padding: 16px 18px; background: #fff; border: 1px solid #d8dee6; border-radius: 8px; }}
    h2 {{ font-size: 20px; margin: 0 0 4px; }}
    .meta {{ color: #5c6b7a; margin-top: 0; }}
    .stack {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 0; list-style: none; }}
    .stack li {{ background: #e7eef6; color: #1d4e89; border-radius: 4px; padding: 2px 8px; font-size: 13px; }}
    .empty {{ color: #5c6b7a; font-style: italic; }}
    button {{ font: inherit; padding: 6px 12px; cursor: pointer; background: #fff; color: #1a2332; border: 1px solid #d8dee6; border-radius: 6px; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .actions form {{ display: flex; gap: 8px; align-items: center; margin: 0; }}
    select {{ font: inherit; color: #1a2332; background: #fff; border: 1px solid #d8dee6; border-radius: 6px; padding: 6px 8px; }}
  </style>
</head>
<body>
  <h1>Current Positions</h1>
  <div class="scrape">
    <div class="scrape-actions">
      <form method="post" action="/scrape">
        <button type="submit">Get Latest Jobs</button>
      </form>
      <a class="add-job" href="/add-job">Add a Job</a>
    </div>
    <p class="meta">One page of developer jobs in New Zealand. This takes a few minutes.</p>
  </div>
  <table class="positions">
    <thead>
      <tr><th>Position</th><th>Status</th></tr>
    </thead>
    <tbody>
      {"".join(index_items)}
    </tbody>
  </table>
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
