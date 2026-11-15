import { useCallback, useEffect, useState } from "react";
import { api, backups, type Project, type ProjectSummary, restoreLost, type Status } from "./api";
import { Busy, ErrorNote, ModeContext, useAction } from "./ui";
import Step1 from "./steps/Step1";
import Step2 from "./steps/Step2";
import Step3 from "./steps/Step3";
import Step4 from "./steps/Step4";
import Step5 from "./steps/Step5";

const STEPS = ["Unique Value Zone", "Transformation", "Wissen", "Struktur", "Produkt & PDF"];

function useHashProject(): [string | null, (id: string | null) => void] {
  const read = () => window.location.hash.match(/^#\/p\/(\w+)/)?.[1] ?? null;
  const [id, setId] = useState<string | null>(read);
  useEffect(() => {
    const on = () => setId(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return [id, (next) => { window.location.hash = next ? `#/p/${next}` : "#/"; }];
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [failed, setFailed] = useState("");
  const [projectId, openProject] = useHashProject();
  const [choice, setChoice] = useState(() => { try { return localStorage.getItem("pw-mode"); } catch { return null; } });

  const loadStatus = useCallback(() => {
    api<Status>("GET", "/status").then(setStatus).catch((e) => setFailed(e.message));
  }, []);
  useEffect(() => {
    loadStatus();
    window.addEventListener("pw-unauthorized", loadStatus);
    return () => window.removeEventListener("pw-unauthorized", loadStatus);
  }, [loadStatus]);

  if (failed) return <Shell><ErrorNote message={failed} /></Shell>;
  if (!status) return <Shell><Busy>Lädt</Busy></Shell>;
  if (status.auth_required && !status.authenticated) return <Login onDone={loadStatus} />;

  // Without an API key only copy mode can produce text.
  const manual = !status.has_key || choice === "manual";
  const setManual = (on: boolean) => {
    setChoice(on ? "manual" : "api");
    try { localStorage.setItem("pw-mode", on ? "manual" : "api"); } catch { /* preference just won't persist */ }
  };

  return (
    <ModeContext.Provider value={manual}>
      <Shell onHome={() => openProject(null)} status={status} manual={manual} setManual={setManual}>
        {projectId
          ? <Workspace key={projectId} id={projectId} onBack={() => openProject(null)} />
          : <ProjectList onOpen={openProject} />}
      </Shell>
    </ModeContext.Provider>
  );
}

function Shell({ children, onHome, status, manual, setManual }: {
  children: React.ReactNode; onHome?: () => void; status?: Status; manual?: boolean; setManual?: (on: boolean) => void;
}) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <button onClick={onHome} className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-black text-white">P</span>
            ProduktWerk
          </button>
          <div className="flex flex-wrap items-center justify-end gap-3">
            {status?.mock && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Mock-Modus: Beispieltexte</span>}
            {setManual && status && (
              <div className="flex rounded-lg border border-slate-300 bg-white p-0.5 text-sm font-semibold" role="radiogroup" aria-label="KI-Modus">
                <button role="radio" aria-checked={!manual} disabled={!status.has_key} title={status.has_key ? "Texte kommen automatisch über die API" : "Dafür ist ein ANTHROPIC_API_KEY nötig"}
                  onClick={() => setManual(false)} className={`rounded-md px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 ${!manual ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>Automatisch (API)</button>
                <button role="radio" aria-checked={!!manual} title="Du kopierst Prompts in deinen eigenen Claude-Chat. Keine API-Kosten."
                  onClick={() => setManual(true)} className={`rounded-md px-3 py-1.5 ${manual ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>Kopier-Modus</button>
              </div>
            )}
          </div>
        </div>
      </header>
      {manual && (
        <div className="border-b border-brand-100 bg-brand-50 px-4 py-2.5 text-center text-sm text-brand-700">
          Kopier-Modus: Du kopierst pro Schritt einen Prompt in deinen Claude-Chat und fügst die Antwort hier ein. Es entstehen keine API-Kosten.
        </div>
      )}
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}

function Login({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState("");
  const { busy, error, run } = useAction();
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <form className="card w-full max-w-sm" onSubmit={(e) => { e.preventDefault(); run(async () => { await api("POST", "/login", { password }); onDone(); }); }}>
        <h1 className="text-xl font-bold">ProduktWerk</h1>
        <p className="mt-1 mb-4 text-sm text-slate-600">Bitte Passwort eingeben.</p>
        <label className="label" htmlFor="pw">Passwort</label>
        <input id="pw" type="password" autoFocus className="input mb-3" value={password} onChange={(e) => setPassword(e.target.value)} />
        <ErrorNote message={error} />
        <button className="btn-primary mt-3 w-full" disabled={busy || !password}>{busy ? <Busy>Prüfe</Busy> : "Anmelden"}</button>
      </form>
    </div>
  );
}

function ProjectList({ onOpen }: { onOpen: (id: string) => void }) {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("de");
  const { busy, error, run } = useAction();
  const [restored, setRestored] = useState(0);
  const load = useCallback(() => run(async () => {
    let list = await api<ProjectSummary[]>("GET", "/projects");
    const n = await restoreLost(list.map((p) => p.id));
    if (n) { setRestored(n); list = await api<ProjectSummary[]>("GET", "/projects"); }
    setProjects(list);
  }), [run]);
  useEffect(() => { load(); }, [load]);

  const importFile = (file: File) => run(async () => {
    let data: unknown;
    try { data = JSON.parse(await file.text()); } catch { throw new Error("Die Datei ist keine gültige Sicherung."); }
    const res = await api<{ id: string; restored: boolean }>("POST", "/projects/import", data);
    if (!res.restored) throw new Error("Dieses Projekt ist bereits vorhanden.");
    await load();
  });

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight">Deine Produkte</h1>
      <p className="mt-2 text-slate-600">Von der Nische zum verkaufsfertigen PDF in fünf Schritten. Alles wird automatisch gespeichert.</p>

      <form className="card mt-6 flex flex-wrap items-end gap-3" onSubmit={(e) => {
        e.preventDefault();
        run(async () => onOpen((await api<Project>("POST", "/projects", { name, language })).id));
      }}>
        <div className="min-w-48 flex-1">
          <label className="label" htmlFor="name">Neues Projekt</label>
          <input id="name" className="input" placeholder="Arbeitstitel, z. B. Physio-Guide" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="lang">Sprache des Produkts</label>
          <select id="lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="de">Deutsch</option>
            <option value="en">Englisch</option>
          </select>
        </div>
        <button className="btn-primary" disabled={busy || !name.trim()}>Projekt anlegen</button>
      </form>
      <div className="mt-3 space-y-2">
        <ErrorNote message={error} />
        {restored > 0 && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {restored === 1 ? "1 Projekt wurde" : `${restored} Projekte wurden`} aus der Sicherung in diesem Browser wiederhergestellt.</p>}
      </div>
      <div className="mt-4 flex justify-end">
        <label className="btn-ghost cursor-pointer">
          Sicherung importieren
          <input type="file" accept="application/json,.json" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) importFile(f); e.target.value = ""; }} />
        </label>
      </div>

      <ul className="mt-2 space-y-3">
        {projects?.length === 0 && <li className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-500">Noch keine Projekte. Lege oben dein erstes an.</li>}
        {projects?.map((p) => (
          <li key={p.id} className="card flex items-center justify-between gap-4 p-4">
            <button className="min-w-0 flex-1 text-left" onClick={() => onOpen(p.id)}>
              <span className="block truncate font-semibold">{p.title || p.name}</span>
              <span className="text-sm text-slate-500">
                {p.title ? `${p.name} · ` : ""}Schritt {p.step} von 5 · {new Date(p.updated_at * 1000).toLocaleDateString("de-DE")}
              </span>
            </button>
            <button className="btn-secondary" onClick={() => onOpen(p.id)}>Öffnen</button>
            <button className="btn-danger" aria-label={`${p.name} löschen`} onClick={() => {
              if (confirm(`Projekt „${p.name}" mit allen Texten endgültig löschen?`)) run(async () => { await api("DELETE", `/projects/${p.id}`); backups.remove(p.id); await load(); });
            }}>Löschen</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export type StepProps = { project: Project; setProject: (p: Project) => void; next: () => void };

function Workspace({ id, onBack }: { id: string; onBack: () => void }) {
  const [project, setProject] = useState<Project | null>(null);
  const [view, setView] = useState(1);
  const [error, setError] = useState("");

  const [unsaved, setUnsaved] = useState(false);

  useEffect(() => {
    (async () => {
      let p: Project;
      try {
        p = await api<Project>("GET", `/projects/${id}`);
      } catch (e) {
        // The server may have lost it (restart without a disk): put the browser backup back.
        await restoreLost([]);
        p = await api<Project>("GET", `/projects/${id}`).catch(() => { throw e; });
      }
      setProject(p);
      setView(p.step);
    })().catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => { if (project) setUnsaved(!backups.save(project)); }, [project]);

  const download = () => {
    if (!project) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(project)], { type: "application/json" }));
    Object.assign(document.createElement("a"), { href: url, download: `${project.name.replace(/[^\w-]+/g, "-")}-sicherung.json` }).click();
    URL.revokeObjectURL(url);
  };

  if (error) return <div className="space-y-4"><ErrorNote message={error} /><button className="btn-secondary" onClick={onBack}>Zur Übersicht</button></div>;
  if (!project) return <Busy>Lädt Projekt</Busy>;

  const unlocked = [true, !!project.uvz, !!project.transformation, !!project.transformation, !!project.charter];
  const goto = (n: number) => {
    setView(n);
    window.scrollTo({ top: 0 });
    if (n > project.step) api<Project>("PATCH", `/projects/${id}`, { step: n }).then(setProject).catch(() => {});
  };
  const props: StepProps = { project, setProject, next: () => goto(Math.min(view + 1, 5)) };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
        <button className="font-medium text-brand-600 hover:underline" onClick={onBack}>Alle Projekte</button>
        <span>/</span>
        <span className="font-medium text-slate-800">{project.name}</span>
        <button className="ml-auto font-medium text-brand-600 hover:underline" onClick={download}>Sicherung herunterladen</button>
      </div>
      {unsaved && <p role="alert" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        Die automatische Sicherung in diesem Browser ist fehlgeschlagen (Speicher voll oder blockiert). Lade bitte regelmäßig eine Sicherung herunter.</p>}
      <nav aria-label="Schritte" className="mb-8 overflow-x-auto">
        <ol className="flex min-w-max gap-2">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const active = n === view;
            return (
              <li key={label}>
                <button
                  disabled={!unlocked[i]}
                  aria-current={active ? "step" : undefined}
                  onClick={() => goto(n)}
                  className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${
                    active ? "border-brand-600 bg-brand-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-slate-400"}`}
                >
                  <span className={`grid h-5 w-5 place-items-center rounded-full text-xs ${active ? "bg-white/20" : "bg-slate-100"}`}>{n}</span>
                  {label}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
      {view === 1 && <Step1 {...props} />}
      {view === 2 && <Step2 {...props} />}
      {view === 3 && <Step3 {...props} />}
      {view === 4 && <Step4 {...props} />}
      {view === 5 && <Step5 {...props} />}
    </div>
  );
}
