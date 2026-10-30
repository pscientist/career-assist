import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from generate_tailored_cv import generate_cv
from render_jobs_html import job_seek_id, load_jobs, mark_job_removed, render_jobs_html

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent


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
        if path == "/remove":
            self._remove(job_id)
            return
        if path != "/generate":
            self._html(404, "<p>Not found.</p>")
            return
        # json_path is the scrape file from startup. A newer scrape needs a restart.
        job = find_job(load_jobs(self.json_path), job_id)
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

    def _remove(self, job_id):
        # The scrape file still holds the ad. The status file is what keeps it hidden.
        if not job_id or find_job(load_jobs(self.json_path), job_id) is None:
            self._html(404, "<p>No job with that id.</p>")
            return
        mark_job_removed(job_id)
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
