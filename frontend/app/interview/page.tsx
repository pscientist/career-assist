"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

const QUESTIONS = [
  "Tell me about yourself.",
  "Why are you looking for a new role?",
  "What kind of role are you looking for next?",
  "Walk me through your recent experience.",
  "Why are you interested in this company?",
  "What are your salary expectations?",
  "When could you start?",
  "Are you open to hybrid, remote, or relocation?",
  "Do you have the right to work here?",
  "What are you strongest at?",
  "Tell me about a time you handled a difficult problem at work.",
  "Why should we move you forward?",
  "Do you have any questions for me?",
];

const PREFILL = QUESTIONS.map((question) => `${question}\n`).join("\n");

type Job = {
  id: number;
  title: string;
  company: string;
  status: string;
  prep_notes: string;
};

function authHeaders() {
  const token = localStorage.getItem("careerassist_token");
  if (!token) return null;
  return { Authorization: `Bearer ${token}` };
}

function notesFor(job: Job) {
  return job.prep_notes ? job.prep_notes : PREFILL;
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

export default function InterviewPracticePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to prepare for an interview.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API}/jobs`, { headers });
        if (response.status === 401) {
          if (!cancelled) setMessage("Log in to prepare for an interview.");
          return;
        }
        if (!response.ok) {
          if (!cancelled) setMessage("Could not load jobs.");
          return;
        }
        const body: Job[] = await response.json();
        if (cancelled) return;
        const interviewing = body.filter((job) => job.status === "interviewing");
        setJobs(interviewing);
        if (!interviewing.length) {
          setMessage("No jobs are marked Interviewing.");
          return;
        }
        setJobId(interviewing[0].id);
        setNotes(notesFor(interviewing[0]));
      } catch {
        if (!cancelled) setMessage("Could not load jobs.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function chooseJob(id: number) {
    const job = jobs.find((item) => item.id === id);
    setJobId(id);
    setNotes(job ? notesFor(job) : "");
    setMessage("");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const headers = authHeaders();
    if (!headers || jobId === null) {
      setMessage("Log in to prepare for an interview.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/jobs/${jobId}/prep`, {
        method: "PUT",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (response.status === 401) {
        setMessage("Log in to prepare for an interview.");
        return;
      }
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const saved: Job = await response.json();
      setJobs((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setNotes(notesFor(saved));
      setMessage("Saved.");
    } catch {
      setMessage("Could not save the notes.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Interview Practice</h1>
        <p className="lede">Common questions recruiters ask in a first conversation.</p>
      </header>
      <div className="jobs-card">
        <ol className="question-list">
          {QUESTIONS.map((question) => (
            <li key={question}>{question}</li>
          ))}
        </ol>
      </div>
      {message && <p className="message">{message}</p>}
      {jobs.length > 0 && (
        <form className="add-job" onSubmit={save}>
          <label>
            <span>Interviewing job</span>
            <select
              aria-label="Interviewing job"
              value={jobId ?? ""}
              onChange={(event) => chooseJob(Number(event.target.value))}
            >
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title} — {job.company}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Preparation notes</span>
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        </form>
      )}
    </main>
  );
}
