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

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function login(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const body = await response.json();
      localStorage.setItem("careerassist_token", body.token);
      setMessage(`Logged in as ${body.username}.`);
      setPassword("");
    } catch {
      setMessage("Could not log in.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Login</h1>
        <p className="lede">Use the username and password for your account.</p>
      </header>
      {message && <p className="message">{message}</p>}
      <form className="add-job account" onSubmit={login}>
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
            autoComplete="current-password"
            value={password}
            required
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Logging in..." : "Login"}
        </button>
      </form>
    </main>
  );
}
