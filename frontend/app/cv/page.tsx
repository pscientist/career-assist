"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

type Experience = {
  company: string;
  role: string;
  period: string;
  highlights: string[];
};

type Recommendation = {
  name: string;
  title?: string;
  context?: string;
  quotes: string[];
};

type Profile = {
  name: string;
  url: string;
  highlights: string[];
};

type Education = {
  institution: string;
  qualifications: string[];
};

type MasterCv = {
  name: string;
  contact: Record<string, string>;
  core_skills: string[];
  experiences: Experience[];
  recommendations: Recommendation[];
  online_profiles: Profile[];
  education: Education[];
  interests: string;
};

const CONTACT_LABELS: Record<string, string> = {
  email: "Email",
  linkedin: "LinkedIn",
  self_intro: "Intro",
  github: "GitHub",
  github_dev: "Dev.to",
  youtube: "YouTube",
};

function isCurrent(experience: Experience) {
  return experience.period.toLowerCase().includes("present");
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

function ContactValue({ value }: { value: string }) {
  if (value.startsWith("http")) {
    return <a href={value}>{value}</a>;
  }
  if (value.includes("@")) {
    return <a href={`mailto:${value}`}>{value}</a>;
  }
  return value;
}

export default function MasterCvPage() {
  const [cv, setCv] = useState<MasterCv | null>(null);
  const [highlights, setHighlights] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API}/master-cv`);
        if (!response.ok) {
          if (!cancelled) setMessage(await errorMessage(response));
          return;
        }
        const body: MasterCv = await response.json();
        if (cancelled) return;
        setCv(body);
        const current = body.experiences.find(isCurrent);
        setHighlights(current ? [...current.highlights] : []);
      } catch {
        if (!cancelled) setMessage("Could not load the master CV.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function updateHighlight(index: number, value: string) {
    setHighlights(highlights.map((highlight, item) => (item === index ? value : highlight)));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/master-cv/current-highlights`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ highlights }),
      });
      if (!response.ok) {
        setMessage(await errorMessage(response));
        return;
      }
      const body: MasterCv = await response.json();
      setCv(body);
      const current = body.experiences.find(isCurrent);
      setHighlights(current ? [...current.highlights] : []);
      setMessage("Saved.");
    } catch {
      setMessage("Could not save the highlights.");
    } finally {
      setSaving(false);
    }
  }

  const current = cv?.experiences.find(isCurrent);
  const earlier = cv?.experiences.filter((experience) => experience !== current) ?? [];

  return (
    <main>
      <header className="hero">
        <h1>Master CV</h1>
        {cv && <p className="lede">{cv.name}</p>}
      </header>
      {message && <p className="message">{message}</p>}
      {cv && (
        <ul className="contact-list">
          {Object.entries(cv.contact).map(([key, value]) => (
            <li key={key}>
              <span>{CONTACT_LABELS[key] || key}</span>
              <ContactValue value={value} />
            </li>
          ))}
        </ul>
      )}
      {current && (
        <form className="add-job master-cv" onSubmit={save}>
          <h2>{current.role}</h2>
          <p className="meta">
            {current.company} · {current.period}
          </p>
          {highlights.map((highlight, index) => (
            <div className="highlight-row" key={index}>
              <label>
                <span>Highlight {index + 1}</span>
                <textarea
                  className="highlight"
                  value={highlight}
                  onChange={(event) => updateHighlight(index, event.target.value)}
                />
              </label>
              <button
                type="button"
                className="quiet"
                onClick={() => setHighlights(highlights.filter((_, item) => item !== index))}
              >
                Remove
              </button>
            </div>
          ))}
          <div className="scrape-actions">
            <button type="button" className="quiet" onClick={() => setHighlights([...highlights, ""])}>
              Add highlight
            </button>
            <button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save highlights"}
            </button>
          </div>
        </form>
      )}
      {cv && (
        <div className="jobs-card cv-rest">
          <section>
            <h2>Earlier roles</h2>
            {earlier.map((experience) => (
              <div key={`${experience.company}-${experience.period}`}>
                <h3>
                  {experience.role}
                  <span>
                    {experience.company} · {experience.period}
                  </span>
                </h3>
                <ul>
                  {experience.highlights.map((highlight, index) => (
                    <li key={index}>{highlight}</li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
          <section>
            <h2>Core skills</h2>
            <p>{cv.core_skills.join(", ")}</p>
          </section>
          <section>
            <h2>Recommendations</h2>
            {cv.recommendations.map((item) => (
              <div key={item.name}>
                <h3>
                  {item.name}
                  <span>{[item.title, item.context].filter(Boolean).join(" · ")}</span>
                </h3>
                {item.quotes.map((quote, index) => (
                  <p key={index}>{quote}</p>
                ))}
              </div>
            ))}
          </section>
          <section>
            <h2>Online profiles</h2>
            {cv.online_profiles.map((profile) => (
              <div key={profile.name}>
                <h3>
                  <a href={profile.url}>{profile.name}</a>
                </h3>
                <ul>
                  {profile.highlights.map((highlight, index) => (
                    <li key={index}>{highlight}</li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
          <section>
            <h2>Education</h2>
            {cv.education.map((item) => (
              <div key={item.institution}>
                <h3>{item.institution}</h3>
                <ul>
                  {item.qualifications.map((qualification) => (
                    <li key={qualification}>{qualification}</li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
          <section>
            <h2>Interests</h2>
            <p>{cv.interests}</p>
          </section>
        </div>
      )}
    </main>
  );
}
