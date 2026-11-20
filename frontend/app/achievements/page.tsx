"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

type Achievement = {
  id: number;
  achievement: string;
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

export default function WeeklyAchievementsPage() {
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to see your achievements.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API}/achievements`, { headers });
        if (response.status === 401) {
          if (!cancelled) setMessage("Log in to see your achievements.");
          return;
        }
        if (!response.ok) {
          if (!cancelled) setMessage("Could not load achievements.");
          return;
        }
        const body: Achievement[] = await response.json();
        if (!cancelled) setAchievements(body);
      } catch {
        if (!cancelled) setMessage("Could not load achievements.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function addAchievement(event: FormEvent) {
    event.preventDefault();
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to see your achievements.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/achievements`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ achievement: draft }),
      });
      if (response.status === 401) {
        setMessage("Log in to see your achievements.");
        return;
      }
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const achievement: Achievement = await response.json();
      setAchievements([achievement, ...achievements]);
      setDraft("");
    } catch {
      setMessage("Could not save the achievement.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Weekly Achievements</h1>
        <p className="lede">Quizzes, tips, and notes from the week.</p>
      </header>
      {message && <p className="message">{message}</p>}
      <form className="add-job" onSubmit={addAchievement}>
        <label>
          <span>Achievement</span>
          <textarea
            value={draft}
            required
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Add achievement"}
        </button>
      </form>
      <div className="jobs-card">
        {achievements.length === 0 ? (
          <p className="empty">No achievements yet.</p>
        ) : (
          <ul className="question-list">
            {achievements.map((item) => (
              <li key={item.id}>
                {item.achievement}
                {item.created_at && <div className="meta">{when(item.created_at)}</div>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
