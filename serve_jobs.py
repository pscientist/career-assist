import html
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from generate_tailored_cv import generate_cv
from job_store import add_manual_job, clear_status, manual_jobs, set_status
from render_jobs import job_seek_id, load_jobs, render_jobs_html

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
# One scrape at a time. A second click would launch another browser against Seek.
scrape_lock = threading.Lock()


def latest_jobs_json():
    matches = sorted(ROOT.glob("seek_jobs_with_stack_*.json"))
    if not matches:
        raise SystemExit("No seek_jobs_with_stack_*.json file found")
    return matches[-1]


def find_job(jobs, job_id):
    for job in jobs:
        # Older scrape files have no id field; job_seek_id reads it from the Seek URL.
        if job_seek_id(job) == job_id:
            found = dict(job)
            found["id"] = job_id
            return found
    return None


def find_listed_job(json_path, job_id):
    found = find_job(load_jobs(json_path), job_id)
    if found is not None:
        return found
    return find_job(manual_jobs(), job_id)


def _field(fields, name):
    return (fields.get(name) or [""])[0].strip()


def add_job_page(values=None, message=""):
    values = values or {}

    def value(name):
        return html.escape(values.get(name) or "", quote=True)

    notice = f'<p class="message">{html.escape(message)}</p>' if message else ""
    fields_html = []
    for name, label in (
        ("title", "Title"),
        ("company", "Company"),
        ("location", "Location"),
        ("url", "URL"),
        ("seek_id", "Seek id"),
        ("source", "Source"),
        ("tech_stack", "Tech stack"),
    ):
        required = " required" if name in ("title", "company") else ""
        placeholder = ' placeholder="react, python, aws"' if name == "tech_stack" else ""
        fields_html.append(
            f'<label><span>{label}</span><input name="{name}" value="{value(name)}"{required}{placeholder}></label>'
        )
    fields_html = "\n".join(fields_html)
    requirements = html.escape(values.get("requirements") or "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Add a Job</title>
  <style>
    body {{ font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; margin: 40px auto; max-width: 760px; background: #f4f6f8; color: #1a2332; line-height: 1.5; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 3px solid #1d4e89; }}
    a {{ color: #1d4e89; text-decoration: none; }}
    form {{ margin-top: 20px; padding: 16px 18px; background: #fff; border: 1px solid #d8dee6; border-radius: 8px; }}
    label {{ display: block; margin: 12px 0; }}
    span {{ display: block; margin-bottom: 4px; }}
    input, textarea {{ font: inherit; width: 100%; box-sizing: border-box; color: #1a2332; background: #fff; border: 1px solid #d8dee6; border-radius: 6px; padding: 6px 8px; }}
    textarea {{ min-height: 220px; }}
    button {{ font: inherit; margin-top: 8px; padding: 6px 12px; cursor: pointer; background: #1d4e89; color: #fff; border: 1px solid #1d4e89; border-radius: 6px; }}
    .message {{ color: #1d4e89; font-weight: 600; }}
    .meta {{ color: #5c6b7a; }}
  </style>
</head>
<body>
  <h1>Add a Job</h1>
  <p><a href="/">Back to jobs</a></p>
  {notice}
  <form method="post" action="/add-job">
    {fields_html}
    <label><span>Requirements</span><textarea name="requirements">{requirements}</textarea></label>
    <button type="submit">Add job</button>
  </form>
  <p class="meta">Title and company are required. Leave Seek id blank when the job has no Seek number.</p>
</body>
</html>
"""


class JobsHandler(BaseHTTPRequestHandler):
    # Set on the class in main(). A new handler is created for every request,
    # so these cannot be passed through __init__ without replacing the server.
    json_path = None
    jobs_page = ""

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._redirect("/" + self.jobs_page)
            return
        if path == "/add-job":
            self._html(200, add_job_page())
            return
        relative = path.lstrip("/")
        target = (ROOT / relative).resolve()
        # resolve() collapses ".." so a request cannot read files outside this folder.
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self._html(404, "<p>Not found.</p>")
            return
        data = target.read_bytes()
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        fields = parse_qs(self.rfile.read(length).decode("utf-8"))
        job_id = (fields.get("id") or [""])[0].strip()
        if path == "/scrape": # Get the latest Jobs
            self._scrape()
            return
        if path == "/add-job":
            self._add_job(fields)
            return
        if path == "/remove": # Remove the Job
            self._save_status(job_id, "deleted")
            return
        if path == "/status":
            status = (fields.get("status") or [""])[0].strip()
            if status == "new":
                self._clear_status(job_id)
            elif status in ("applied", "interviewing"):
                self._save_status(job_id, status)
            else:
                self._html(400, "<p>Unknown status.</p>")
            return
        if path != "/generate": # Generate CV
            self._html(404, "<p>Not found.</p>")
            return
        # json_path is the scrape file currently shown. /scrape replaces it when a run finishes.
        job = find_listed_job(self.json_path, job_id)
        if job is None:
            self._html(404, "<p>No job with that id.</p>")
            return
        try:
            filename = generate_cv(job)
        except Exception as error:
            self._html(500, f"<p>Could not generate the CV.</p><pre>{html.escape(str(error))}</pre>")
            return
        # 303 sends the browser to the CV with GET, so a refresh does not generate it again.
        self._redirect("/" + filename)

    def _scrape(self):
        if not scrape_lock.acquire(blocking=False):
            self._html(409, "<p>A scrape is already running.</p>")
            return
        try:
            # The server may inherit a sandbox browser cache that has no Chromium.
            # Playwright's own cache already has the browser.
            env = os.environ.copy()
            env.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            # scrape-seek.py cannot be imported; the hyphen is not a module name.
            result = subprocess.run(
                [sys.executable, str(ROOT / "scrape-seek.py")],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
            if result.stderr:
                print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "Scrape failed.").strip()
                self._html(500, f"<p>Could not scrape Seek.</p><pre>{html.escape(detail)}</pre>")
                return
            json_path = latest_jobs_json()
            html_path = Path(render_jobs_html(json_path))
            JobsHandler.json_path = json_path
            JobsHandler.jobs_page = html_path.name
            self._redirect("/" + html_path.name)
        finally:
            scrape_lock.release()

    def _clear_status(self, job_id):
        if not job_id or find_listed_job(self.json_path, job_id) is None:
            self._html(404, "<p>No job with that id.</p>")
            return
        clear_status(job_id)
        render_jobs_html(self.json_path)
        self._redirect("/" + self.jobs_page)

    def _save_status(self, job_id, status, next_appt_date=None):
        # The scrape file still holds the ad. The database is what keeps the status.
        if not job_id or find_listed_job(self.json_path, job_id) is None:
            self._html(404, "<p>No job with that id.</p>")
            return
        try:
            set_status(job_id, status, next_appt_date)
        except ValueError:
            self._html(400, "<p>The appointment date must be YYYY-MM-DD.</p>")
            return
        render_jobs_html(self.json_path)
        self._redirect("/" + self.jobs_page)

    def _add_job(self, fields):
        values = {
            "title": _field(fields, "title"),
            "company": _field(fields, "company"),
            "location": _field(fields, "location"),
            "url": _field(fields, "url"),
            "seek_id": _field(fields, "seek_id"),
            "source": _field(fields, "source"),
            "tech_stack": _field(fields, "tech_stack"),
            "requirements": (fields.get("requirements") or [""])[0].strip(),
        }
        if not values["title"] or not values["company"]:
            self._html(400, add_job_page(values, "Title and company are required."))
            return
        tech_stack = [part.strip() for part in values["tech_stack"].split(",") if part.strip()]
        try:
            add_manual_job(
                values["title"],
                values["company"],
                values["location"],
                values["url"],
                values["seek_id"],
                values["source"],
                tech_stack,
                values["requirements"],
            )
        except ValueError as error:
            self._html(400, add_job_page(values, str(error)))
            return
        render_jobs_html(self.json_path)
        self._redirect("/" + self.jobs_page)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _html(self, status, body):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    os.chdir(ROOT)
    json_path = latest_jobs_json()
    html_path = Path(render_jobs_html(json_path))
    JobsHandler.json_path = json_path
    JobsHandler.jobs_page = html_path.name
    # One thread per request. Generating a CV calls the API and would otherwise block the page.
    server = ThreadingHTTPServer((HOST, PORT), JobsHandler)
    print(f"Open http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
