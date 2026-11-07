const FIXED: Record<string, string> = {
  fastapi: "FastAPI",
  ai: "AI",
  openai: "OpenAI",
  "c#": "C#",
  ".net": ".NET",
  net: "NET",
  "c++": "C++",
};

export function techLabel(term: string) {
  const key = term.trim().toLowerCase();
  if (FIXED[key]) return FIXED[key];
  return key
    .split(" ")
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : word))
    .join(" ");
}
