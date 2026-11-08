"use client";

import { FormEvent, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

async function errorMessage(response: Response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // The response was not JSON.
  }
  return "Something went wrong.";
}

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function register(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, username, password }),
      });
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const body = await response.json();
      localStorage.setItem("careerassist_token", body.token);
      window.dispatchEvent(new Event("careerassist-auth"));
      setMessage(`Registered as ${body.name}.`);
      setPassword("");
    } catch {
      setMessage("Could not register.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Register</h1>
        <p className="lede">Create an account so the jobs you add stay with you.</p>
      </header>
      {message && <p className="message">{message}</p>}
      <form className="add-job account" onSubmit={register}>
        <label>
          <span>Name</span>
          <input
            name="name"
            autoComplete="name"
            value={name}
            required
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          <span>Username</span>
          <input
            name="username"
            autoComplete="username"
            value={username}
            required
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          <span>Password</span>
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            required
            minLength={8}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Registering..." : "Register"}
        </button>
        <p className="meta">Use at least 8 characters for the password.</p>
      </form>
    </main>
  );
}
