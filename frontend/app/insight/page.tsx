"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

type Job = {
  tech_stack: string[];
};

type ShareRow = {
  tech: string;
  jobs: number;
  share: number;
};

function techShare(jobs: Job[]): ShareRow[] {
  const counts = new Map<string, number>();
  for (const job of jobs) {
    const seen = new Set((job.tech_stack || []).map((term) => term.trim()).filter(Boolean));
    for (const tech of seen) {
      counts.set(tech, (counts.get(tech) || 0) + 1);
    }
  }
  const total = jobs.length;
  return [...counts.entries()]
    .map(([tech, count]) => ({
      tech,
      jobs: count,
      share: total === 0 ? 0 : Math.round((count / total) * 100),
    }))
    .sort((a, b) => b.jobs - a.jobs || a.tech.localeCompare(b.tech));
}

export default function InsightPage() {
  const [rows, setRows] = useState<ShareRow[]>([]);
  const [empty, setEmpty] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const response = await fetch(`${API}/jobs?include_deleted=true`);
      if (!response.ok) {
        if (!cancelled) setMessage("Something went wrong.");
        return;
      }
      const jobs: Job[] = await response.json();
      if (cancelled) return;
      setEmpty(jobs.length === 0);
      setRows(techShare(jobs));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main>
      <header className="hero">
        <h1>Job Market Insight</h1>
      </header>
      {message && <p className="message">{message}</p>}
      <div className="jobs-card">
        <table className="share">
          <thead>
            <tr>
              <th>Tech</th>
              <th>Jobs</th>
              <th>Share</th>
            </tr>
          </thead>
          <tbody>
            {empty && (
              <tr>
                <td colSpan={3}>No jobs yet.</td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={row.tech}>
                <td>{row.tech}</td>
                <td>{row.jobs}</td>
                <td>{row.share}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
