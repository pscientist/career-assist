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

export default function InterviewPracticePage() {
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
    </main>
  );
}
