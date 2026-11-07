import asyncio
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.db import ROOT, init_db
from app.models.jobs import add_job, get_job, list_jobs, save_requirements, set_status, update_job, upsert_scraped
from app.models.notes import add_note, list_notes
from app.models.users import delete_session, login_user, register_user, user_for_token
from app.services.cv import generate_cv, master_cv_for_editor, save_current_highlights
from app.services.insight import analyse_ai_skills, load_market_insight, save_market_insight
from app.services.scrape import extract_tech_stack, scrape_seek_nz

# From backend/: ../venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765
HOST = "127.0.0.1"
PORT = 8765
CV_NAME = re.compile(r"^CV_[\w.-]+\.html$")
scrape_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Empty strings are the defaults.
class JobIn(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    seek_id: str = ""
    tech_stack: str = ""
    requirements: str = ""

# FastAPI matches JSON keys in the request to the fields declared on the class.
class StatusIn(BaseModel):
    status: str


class HighlightsIn(BaseModel):
    highlights: list[str]


class RequirementsIn(BaseModel):
    requirements: str = ""


class NoteIn(BaseModel):
    note: str = ""


class AccountIn(BaseModel):
    name: str = ""
    username: str = ""
    password: str = ""


def _bearer(authorization):
    if not authorization:
        raise HTTPException(401, "Log in first.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Log in first.")
    return token.strip()


def _parsed_stack(title, requirements):
    return extract_tech_stack(f"{title}\n{requirements}")


@app.post("/register")
def register(body: AccountIn):
    try:
        return register_user(body.name, body.username, body.password)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.post("/login")
def login(body: AccountIn):
    account = login_user(body.username, body.password)
    if account is None:
        raise HTTPException(401, "Those details do not match.")
    return account


@app.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    account = user_for_token(_bearer(authorization))
    if account is None:
        raise HTTPException(401, "Log in first.")
    return account


@app.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    delete_session(_bearer(authorization))
    return {"ok": True}


@app.get("/interview-notes")
def interview_notes(authorization: Optional[str] = Header(default=None)):
    account = user_for_token(_bearer(authorization))
    if account is None:
        raise HTTPException(401, "Log in first.")
    return list_notes(account["id"])


@app.post("/interview-notes")
def create_interview_note(body: NoteIn, authorization: Optional[str] = Header(default=None)):
    account = user_for_token(_bearer(authorization))
    if account is None:
        raise HTTPException(401, "Log in first.")
    try:
        return add_note(body.note, account["id"])
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/jobs")
def jobs(include_deleted: bool = False):
    return list_jobs(include_deleted)


@app.post("/jobs")
def create_job(body: JobIn):
    try:
        return add_job(
            body.title,
            body.company,
            body.location,
            body.url,
            body.seek_id,
            _parsed_stack(body.title, body.requirements),
            body.requirements,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.put("/jobs/{job_id}")
def edit_job(job_id: int, body: JobIn):
    try:
        job = update_job(
            job_id,
            body.title,
            body.company,
            body.location,
            body.url,
            body.seek_id,
            _parsed_stack(body.title, body.requirements),
            body.requirements,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if job is None:
        raise HTTPException(404, "No job with that id.")
    return job


@app.put("/jobs/{job_id}/requirements")
def update_requirements(job_id: int, body: RequirementsIn):
    text = body.requirements.strip()
    try:
        job = save_requirements(job_id, text, extract_tech_stack(text))
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if job is None:
        raise HTTPException(404, "No job with that id.")
    return job


@app.post("/jobs/{job_id}/status")
def update_status(job_id: int, body: StatusIn):
    try:
        job = set_status(job_id, body.status.strip())
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if job is None:
        raise HTTPException(404, "No job with that id.")
    return job


@app.post("/scrape")
async def scrape():
    if scrape_lock.locked():
        raise HTTPException(409, "A scrape is already running.")
    async with scrape_lock:
        try:
            scraped = await scrape_seek_nz()
            upsert_scraped(scraped)
        except Exception as error:
            raise HTTPException(500, f"Could not scrape Seek. {error}") from error
    return list_jobs()


@app.get("/insights/ai_in_industry")
def ai_in_industry():
    return load_market_insight()


@app.post("/insights/ai")
def ai_insight():
    try:
        return save_market_insight(analyse_ai_skills())
    except Exception as error:
        raise HTTPException(500, f"Could not analyse AI skills. {error}") from error


@app.get("/master-cv")
def read_master_cv():
    try:
        return master_cv_for_editor()
    except Exception as error:
        raise HTTPException(500, f"Could not read the master CV. {error}") from error


@app.put("/master-cv/current-highlights")
def update_current_highlights(body: HighlightsIn):
    try:
        return save_current_highlights(body.highlights)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except Exception as error:
        raise HTTPException(500, f"Could not save the master CV. {error}") from error


@app.post("/jobs/{job_id}/cv")
def create_cv(job_id: int):
    if get_job(job_id) is None:
        raise HTTPException(404, "No job with that id.")
    try:
        filename = generate_cv(job_id)
    except Exception as error:
        raise HTTPException(500, f"Could not generate the CV. {error}") from error
    return {"filename": filename}


@app.get("/cv/{filename}")
def download_cv(filename: str):
    if not CV_NAME.match(filename):
        raise HTTPException(404, "Not found.")
    path = (ROOT / filename).resolve()
    if path.parent != ROOT or not path.is_file():
        raise HTTPException(404, "Not found.")
    return FileResponse(path, media_type="text/html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
