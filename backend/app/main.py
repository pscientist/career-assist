import asyncio
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.db import ROOT, init_db
from app.models.jobs import add_job, get_job, list_jobs, set_status, upsert_scraped
from app.services.cv import generate_cv
from app.services.scrape import scrape_seek_nz

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


class JobIn(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    seek_id: str = ""
    tech_stack: str = ""
    requirements: str = ""


class StatusIn(BaseModel):
    status: str


def _stack(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


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
            _stack(body.tech_stack),
            body.requirements,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


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
