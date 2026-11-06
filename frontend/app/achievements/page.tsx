const SECTIONS = [
  {
    title: "Technical quizzes",
    items: ["TypeScript basics", "React hooks"],
  },
  {
    title: "Improvement tips",
    items: ["Ask for the team size earlier", "Pause before answering the salary question"],
  },
  {
    title: "Notes",
    items: ["Eating healthy", "Walked 10,000 steps yesterday"],
  },
];

export default function WeeklyAchievementsPage() {
  return (
    <main>
      <header className="hero">
        <h1>Weekly Achievements</h1>
        <p className="lede">Quizzes, tips, and notes from the week.</p>
      </header>
      <div className="jobs-card">
        {SECTIONS.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            <ul className="question-list">
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
