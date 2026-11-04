"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

const STATUS_OPTIONS = [
  ["new", "New"],
  ["applied", "Applied"],
  ["interviewing", "Interviewing"],
] as const;

const STATUS_RANK: Record<string, number> = { new: 0, applied: 1, interviewing: 2 };

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
};

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

function Requirements({ text, terms }: { text: string; terms: string[] }) {
  if (!text.trim()) return <p className="empty">No requirements captured</p>;
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

  return (
    <main>
      <h1>Current Positions</h1>
      <div className="scrape">
        <div className="scrape-actions">
          <button type="button" onClick={scrape} disabled={scraping}>
            {scraping ? "Getting jobs..." : "Get Latest Jobs"}
          </button>
          <a className="add-job" href="/add-job">
            Add a Job
          </a>
        </div>
        <p className="meta">One page of developer jobs in New Zealand. This takes a few minutes.</p>
      </div>
      {message && <p className="message">{message}</p>}

      <table className="positions">
        <thead>
          <tr>
            <th>Position</th>
            <th>Company</th>
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
              <td colSpan={3}>No jobs yet.</td>
            </tr>
          )}
          {listed.map((job) => (
            <tr key={job.id}>
              <td>
                <a href={`#job-${job.id}`}>{job.title}</a>
              </td>
              <td>{job.company}</td>
              <td>{STATUS_OPTIONS.find(([value]) => value === job.status)?.[1] || "New"}</td>
            </tr>
          ))}
        </tbody>
      </table>

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
                <li key={term}>{term}</li>
              ))}
            </ul>
          )}
          <Requirements text={job.requirements} terms={job.tech_stack} />
        </article>
      ))}
    </main>
  );
}
