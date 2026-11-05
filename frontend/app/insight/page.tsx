"use client";

import { useEffect, useState } from "react";
import { techLabel } from "../tech";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

type Job = {
  tech_stack: string[];
  created_at: string;
};

function dayMonthYear(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${date.getFullYear()}`;
}

function summaryLine(jobs: Job[]) {
  const dates = jobs.map((job) => dayMonthYear(job.created_at)).filter(Boolean);
  if (!jobs.length || dates.length !== jobs.length) return "";
  const ordered = [...dates].sort((a, b) => {
    const [ad, am, ay] = a.split("/").map(Number);
    const [bd, bm, by] = b.split("/").map(Number);
    return new Date(ay, am - 1, ad).getTime() - new Date(by, bm - 1, bd).getTime();
  });
  return `From ${jobs.length} jobs between ${ordered[0]} - ${ordered[ordered.length - 1]}`;
}

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
    .sort((a, b) => b.jobs - a.jobs || techLabel(a.tech).localeCompare(techLabel(b.tech)));
}

export default function InsightPage() {
  const [rows, setRows] = useState<ShareRow[]>([]);
  const [summary, setSummary] = useState("");
  const [empty, setEmpty] = useState(false);
  const [message, setMessage] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [analysing, setAnalysing] = useState(false);

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
      setSummary(summaryLine(jobs));
      setRows(techShare(jobs));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function analyse() {
    setAnalysing(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/insights/ai`, { method: "POST" });
      if (!response.ok) {
        setMessage("Could not analyse AI skills.");
        return;
      }
      const body = await response.json();
      setAnalysis(typeof body.analysis === "string" ? body.analysis : "");
    } catch {
      setMessage("Could not analyse AI skills.");
    } finally {
      setAnalysing(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Job Market Insight</h1>
        {summary && <p className="lede">{summary}</p>}
      </header>
      {message && <p className="message">{message}</p>}
      <div className="jobs-card analysis">
        <h2>Summary on AI in the industry</h2>
        <button type="button" className="primary" onClick={analyse} disabled={analysing}>
          {analysing ? "Analysing..." : "Get Insight"}
        </button>
        {analysis && <p>{analysis}</p>}
      </div>
      {rows.length > 0 && (
        <div className="jobs-card">
          <ul className="bars">
            {rows.map((row) => (
              <li key={row.tech}>
                <span className="bar-label">{techLabel(row.tech)}</span>
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${row.share}%` }} />
                </span>
                <span className="bar-value">{row.share}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
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
                <td>{techLabel(row.tech)}</td>
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
