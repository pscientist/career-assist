"use client";

import { FormEvent, useEffect, useState } from "react";
import { techLabel } from "./tech";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

const STATUS_OPTIONS = [
  ["new", "New"],
  ["applied", "Applied"],
  ["interviewing", "Interviewing"],
] as const;

const STATUS_RANK: Record<string, number> = { new: 0, applied: 1, interviewing: 2 };

const QUOTES = [
  ["The only way to do great work is to love what you do.", "Steve Jobs"],
  ["It always seems impossible until it is done.", "Nelson Mandela"],
  ["Start where you are. Use what you have. Do what you can.", "Arthur Ashe"],
  ["Well done is better than well said.", "Benjamin Franklin"],
  ["Do the best you can until you know better. Then when you know better, do better.", "Maya Angelou"],
  ["What you do makes a difference, and you have to decide what kind of difference you want to make.", "Jane Goodall"],
  ["Nothing will work unless you do.", "Maya Angelou"],
] as const;

function quoteOfTheDay() {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const day = Math.floor((now.getTime() - start.getTime()) / 86400000);
  return QUOTES[day % QUOTES.length];
}

type Job = {
  id: number;
  seek_id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  tech_stack: string[];
  requirements: string;
  status: string;
  created_at: string;
};

function createdDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const period = date.getHours() >= 12 ? "pm" : "am";
  const hours = String(date.getHours() % 12 || 12).padStart(2, "0");
  return `${day}/${month} ${hours}:${minutes} ${period}`;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlight(text: string, terms: string[]) {
  const usable = terms.filter(Boolean).sort((a, b) => b.length - a.length);
  if (!usable.length) return text;
  const pattern = new RegExp(`\\b(?:${usable.map(escapeRegExp).join("|")})\\b`, "gi");
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    parts.push(text.slice(last, index));
    parts.push(<strong key={`${index}-${match[0]}`}>{match[0]}</strong>);
    last = index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

function RequirementsEditor({ jobId, onSaved }: { jobId: number; onSaved: (job: Job) => void }) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${API}/jobs/${jobId}/requirements`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements: text }),
      });
      if (!response.ok) {
        setError(await errorMessage(response));
        return;
      }
      onSaved(await response.json());
    } catch {
      setError("Could not save the requirements.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="requirements-edit" onSubmit={save}>
      <label>
        <span>Requirements</span>
        <textarea value={text} onChange={(event) => setText(event.target.value)} />
      </label>
      {error && <p className="message">{error}</p>}
      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </button>
    </form>
  );
}

function Requirements({ text, terms }: { text: string; terms: string[] }) {
  return text
    .trim()
    .split(/\n\s*\n/)
    .map((block, blockIndex) => (
      <p key={blockIndex}>
        {block.split("\n").map((line, lineIndex) => (
          <span key={lineIndex}>
            {lineIndex > 0 && <br />}
            {highlight(line, terms)}
          </span>
        ))}
      </p>
    ));
}

async function errorMessage(response: Response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // The response was not JSON.
  }
  return "Something went wrong.";
}

export default function Page() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [message, setMessage] = useState("");
  const [scraping, setScraping] = useState(false);
  const [cvJobId, setCvJobId] = useState<number | null>(null);
  const [cvLinks, setCvLinks] = useState<Record<number, string>>({});
  const [statusOrder, setStatusOrder] = useState<"asc" | "desc" | null>(null);

  const listed = statusOrder
    ? [...jobs].sort((a, b) => {
        const diff = (STATUS_RANK[a.status] ?? 0) - (STATUS_RANK[b.status] ?? 0);
        return statusOrder === "asc" ? diff : -diff;
      })
    : jobs;

  async function loadJobs() {
    const response = await fetch(`${API}/jobs`);
    if (!response.ok) {
      setMessage(await errorMessage(response));
      return;
    }
    setJobs(await response.json());
  }

  useEffect(() => {
    loadJobs().catch(() => setMessage("Could not load jobs."));
  }, []);

  async function scrape() {
    setScraping(true);
    setMessage("Getting the latest jobs. This takes a few minutes.");
    try {
      const response = await fetch(`${API}/scrape`, { method: "POST" });
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      setJobs(await response.json());
      setMessage("");
    } catch {
      setMessage("Could not scrape Seek.");
    } finally {
      setScraping(false);
    }
  }

  async function changeStatus(jobId: number, status: string) {
    setMessage("");
    const response = await fetch(`${API}/jobs/${jobId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) {
      setMessage(await errorMessage(response));
      return;
    }
    await loadJobs();
  }

  async function generateCv(jobId: number) {
    setCvJobId(jobId);
    setMessage("Generating the CV...");
    try {
      const response = await fetch(`${API}/jobs/${jobId}/cv`, { method: "POST" });
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const body = await response.json();
      const href = `${API}/cv/${body.filename}`;
      setCvLinks((current) => ({ ...current, [jobId]: href }));
      setMessage("");
      window.open(href, "_blank", "noopener,noreferrer");
    } catch {
      setMessage("Could not generate the CV.");
    } finally {
      setCvJobId(null);
    }
  }

  const [quote, author] = quoteOfTheDay();

  return (
    <main>
      <header className="hero">
        <h1>Your Job Search Companion</h1>
        <p className="lede">
          Find opportunities, tailor your applications, and keep a positive, focused mindset throughout your career
          journey.
        </p>
        <p className="quote">
          “{quote}” — {author}
        </p>
        <div className="scrape-actions">
          <button type="button" className="primary" onClick={scrape} disabled={scraping}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="6" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            {scraping ? "Getting jobs..." : "Get Latest Jobs"}
          </button>
          <a className="add-job" href="/add-job">
            + Add a Job
          </a>
        </div>
        <p className="meta">One page of developer jobs in New Zealand. This takes a few minutes.</p>
      </header>
      {message && <p className="message">{message}</p>}

      <div className="jobs-card">
      <table className="positions">
        <thead>
          <tr>
            <th>Position</th>
            <th>Company</th>
            <th>Added</th>
            <th>
              <span className="status-heading">
                Status
                <button
                  type="button"
                  className="sort"
                  aria-label="Sort by status"
                  onClick={() => setStatusOrder((current) => (current === "asc" ? "desc" : "asc"))}
                >
                  {statusOrder === "desc" ? "↓" : "↑"}
                </button>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {listed.length === 0 && (
            <tr>
              <td colSpan={4}>No jobs yet.</td>
            </tr>
          )}
          {listed.map((job) => (
            <tr key={job.id}>
              <td>
                <a href={`#job-${job.id}`}>{job.title}</a>
                {job.tech_stack.length > 0 && (
                  <ul className="stack">
                    {job.tech_stack.map((term) => (
                      <li key={term}>{techLabel(term)}</li>
                    ))}
                  </ul>
                )}
              </td>
              <td>{job.company}</td>
              <td className="added">{createdDate(job.created_at)}</td>
              <td>
                <span className={`pill pill-${job.status}`}>
                  {STATUS_OPTIONS.find(([value]) => value === job.status)?.[1] || "New"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      {listed.map((job) => (
        <article key={job.id} id={`job-${job.id}`}>
          <h2>{job.title}</h2>
          <p className="meta">
            {job.company}
            {job.location ? ` · ${job.location}` : ""}
          </p>
          {job.url && (
            <p>
              <a href={job.url} target="_blank" rel="noopener noreferrer">
                View on Seek
              </a>
            </p>
          )}
          <div className="actions">
            <button type="button" onClick={() => generateCv(job.id)} disabled={cvJobId === job.id}>
              {cvJobId === job.id ? "Generating..." : "Generate CV"}
            </button>
            {cvLinks[job.id] && (
              <a href={cvLinks[job.id]} target="_blank" rel="noopener noreferrer">
                Open CV
              </a>
            )}
            <select
              aria-label="Status"
              value={STATUS_OPTIONS.some(([value]) => value === job.status) ? job.status : "new"}
              onChange={(event) => changeStatus(job.id, event.target.value)}
            >
              {STATUS_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => changeStatus(job.id, "deleted")}>
              Remove
            </button>
          </div>
          {job.tech_stack.length > 0 && (
            <ul className="stack">
              {job.tech_stack.map((term) => (
                <li key={term}>{techLabel(term)}</li>
              ))}
            </ul>
          )}
          {job.requirements.trim() ? (
            <Requirements text={job.requirements} terms={job.tech_stack} />
          ) : (
            <RequirementsEditor
              jobId={job.id}
              onSaved={(saved) =>
                setJobs((current) => current.map((item) => (item.id === saved.id ? saved : item)))
              }
            />
          )}
        </article>
      ))}
    </main>
  );
}
