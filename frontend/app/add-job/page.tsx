"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

const emptyForm = {
  title: "",
  company: "",
  location: "",
  url: "",
  seek_id: "",
  requirements: "",
};

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

export default function AddJobPage() {
  const router = useRouter();
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authHeaders()) setMessage("Log in to see your jobs.");
  }, []);

  async function addJob(event: FormEvent) {
    event.preventDefault();
    const headers = authHeaders();
    if (!headers) {
      setMessage("Log in to see your jobs.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/jobs`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (response.status === 401) {
        setMessage("Log in to see your jobs.");
        return;
      }
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      router.push("/");
    } catch {
      setMessage("Could not add the job.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <h1>Add a Job</h1>
      <p>
        <a href="/">Back to jobs</a>
      </p>
      {message && <p className="message">{message}</p>}
      <form className="add-job" onSubmit={addJob}>
        {(
          [
            ["title", "Title", true],
            ["company", "Company", true],
            ["location", "Location", false],
            ["url", "URL", false],
            ["seek_id", "Seek id", false],
          ] as const
        ).map(([name, label, required]) => (
          <label key={name}>
            <span>{label}</span>
            <input
              name={name}
              value={form[name]}
              required={required}
              onChange={(event) => setForm({ ...form, [name]: event.target.value })}
            />
          </label>
        ))}
        <label>
          <span>Requirements</span>
          <textarea
            name="requirements"
            value={form.requirements}
            onChange={(event) => setForm({ ...form, requirements: event.target.value })}
          />
        </label>
        <button type="submit" disabled={saving}>
          Add job
        </button>
        <p className="meta">Title and company are required. Leave Seek id blank when the job has no Seek number.</p>
      </form>
    </main>
  );
}
