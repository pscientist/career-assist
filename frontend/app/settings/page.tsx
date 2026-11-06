const SETTINGS = [
  {
    title: "Locale",
    name: "locale",
    selected: "nz",
    options: [
      ["nz", "New Zealand"],
      ["au", "Australia"],
      ["uk", "United Kingdom"],
    ],
  },
  {
    title: "Language",
    name: "language",
    selected: "en",
    options: [
      ["en", "English"],
      ["zh", "中文"],
    ],
  },
  {
    title: "Appearance",
    name: "appearance",
    selected: "light",
    options: [
      ["light", "Light"],
      ["dark", "Dark"],
    ],
  },
] as const;

export default function SettingsPage() {
  return (
    <main>
      <header className="hero">
        <h1>Settings</h1>
        <p className="lede">These choices are for when there is more than one user.</p>
      </header>
      <div className="jobs-card">
        {SETTINGS.map((setting) => (
          <section key={setting.name}>
            <h2>{setting.title}</h2>
            <select name={setting.name} defaultValue={setting.selected} disabled>
              {setting.options.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </section>
        ))}
      </div>
    </main>
  );
}
