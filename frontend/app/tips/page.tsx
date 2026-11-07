"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

type Note = {
  id: number;
  note: string;
  created_at: string;
};

function when(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString();
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

function authHeaders() {
  const token = localStorage.getItem("careerassist_token");
  if (!token) return null;
  return { Authorization: `Bearer ${token}` };
}

export default function ImprovementTipsPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to see your notes.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API}/interview-notes`, { headers });
        if (response.status === 401) {
          if (!cancelled) setMessage("Log in to see your notes.");
          return;
        }
        if (!response.ok) {
          if (!cancelled) setMessage("Could not load notes.");
          return;
        }
        const body: Note[] = await response.json();
        if (!cancelled) setNotes(body);
      } catch {
        if (!cancelled) setMessage("Could not load notes.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function addNote(event: FormEvent) {
    event.preventDefault();
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to see your notes.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/interview-notes`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ note: draft }),
      });
      if (response.status === 401) {
        setMessage("Log in to see your notes.");
        return;
      }
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const note: Note = await response.json();
      setNotes([note, ...notes]);
      setDraft("");
    } catch {
      setMessage("Could not save the note.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Improvement Tips</h1>
        <p className="lede">Notes from past interviews.</p>
      </header>
      {message && <p className="message">{message}</p>}
      <form className="add-job" onSubmit={addNote}>
        <label>
          <span>Note</span>
          <textarea
            value={draft}
            required
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Add note"}
        </button>
      </form>
      <div className="jobs-card">
        {notes.length === 0 ? (
          <p className="empty">No notes yet.</p>
        ) : (
          <ul className="question-list">
            {notes.map((item) => (
              <li key={item.id}>
                {item.note}
                {item.created_at && <div className="meta">{when(item.created_at)}</div>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
