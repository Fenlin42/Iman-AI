import { useState } from "react";
import { api, type Project } from "../api";
import type { StepProps } from "../App";
import { Busy, ErrorNote, Footer, ManualBox, StepHeader, useAction } from "../ui";

export default function Step3({ project, setProject, next }: StepProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const note = useAction();
  const link = useAction();
  const base = `/projects/${project.id}/references`;
  const total = project.references.reduce((n, r) => n + r.content.length, 0);

  return (
    <section>
      <StepHeader title="Quellen und Wissen" lead="Dein Produkt fasst zusammen, was Studien und Experten sagen. Dafür braucht es echte Quellen. Lass sie hier recherchieren oder füge eigene Notizen, Transkripte und Links hinzu." />
      <div className="mb-6">
        <ManualBox title="Echte Studien und Quellen recherchieren lassen (Websuche im Claude-Chat einschalten)" submitLabel="Als Quelle speichern"
          getPrompt={async () => (await api<{ prompt: string }>("POST", `/projects/${project.id}/prompt`, { kind: "sources" })).prompt}
          onSubmit={async (answer) => setProject(await api<Project>("POST", base, { type: "note", title: "Recherchierte Quellen", content: answer }))} />
        <p className="mt-2 text-sm text-slate-600">Öffne danach zwei oder drei der Links selbst und prüfe, ob dort wirklich steht, was die Zusammenfassung behauptet. Ohne gespeicherte Quellen markiert die KI Fakten im Text mit [PRÜFEN].</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <form className="card" onSubmit={(e) => {
          e.preventDefault();
          note.run(async () => { setProject(await api<Project>("POST", base, { type: "note", title, content })); setTitle(""); setContent(""); });
        }}>
          <h3 className="mb-3 font-bold">Text einfügen</h3>
          <label className="label" htmlFor="ref-title">Bezeichnung</label>
          <input id="ref-title" className="input mb-3" placeholder="z. B. Transkript Workshop März" value={title} onChange={(e) => setTitle(e.target.value)} />
          <label className="label" htmlFor="ref-content">Inhalt</label>
          <textarea id="ref-content" rows={8} className="input" placeholder="Notizen, Transkript oder Text hier einfügen …" value={content} onChange={(e) => setContent(e.target.value)} />
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="text-xs text-slate-500">{content.length.toLocaleString("de-DE")} Zeichen</span>
            <button className="btn-primary" disabled={note.busy || content.trim().length < 10}>Hinzufügen</button>
          </div>
          <div className="mt-3"><ErrorNote message={note.error} /></div>
        </form>

        <form className="card self-start" onSubmit={(e) => {
          e.preventDefault();
          link.run(async () => { setProject(await api<Project>("POST", base, { type: "url", url })); setUrl(""); });
        }}>
          <h3 className="mb-3 font-bold">Link einlesen</h3>
          <label className="label" htmlFor="ref-url">Adresse</label>
          <input id="ref-url" type="url" className="input" placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} />
          <p className="mt-2 text-xs text-slate-500">Der Text der Seite wird abgerufen und gespeichert. Seiten hinter Login oder mit reinem JavaScript-Inhalt funktionieren nicht.</p>
          <button className="btn-primary mt-3" disabled={link.busy || !url.trim()}>{link.busy ? <Busy>Lese Seite</Busy> : "Einlesen"}</button>
          <div className="mt-3"><ErrorNote message={link.error} /></div>
        </form>
      </div>

      <h3 className="mt-8 mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Gespeicherte Referenzen ({project.references.length}){total > 0 && ` · ${total.toLocaleString("de-DE")} Zeichen`}
      </h3>
      {project.references.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">Noch nichts hinzugefügt.</p>}
      <ul className="space-y-3">
        {project.references.map((r) => (
          <li key={r.id} className="card flex items-start justify-between gap-4 p-4">
            <div className="min-w-0">
              <p className="font-semibold">{r.title}</p>
              {r.url && <p className="truncate text-xs text-brand-600">{r.url}</p>}
              <p className="mt-1 line-clamp-2 text-sm text-slate-600">{r.content.slice(0, 300)}</p>
              <p className="mt-1 text-xs text-slate-400">{r.content.length.toLocaleString("de-DE")} Zeichen</p>
            </div>
            <button className="btn-danger shrink-0" onClick={() => note.run(async () => setProject(await api<Project>("DELETE", `${base}/${r.id}`)))}>Entfernen</button>
          </li>
        ))}
      </ul>
      <Footer><button className="btn-primary" onClick={next}>{project.references.length ? "Weiter zur Struktur" : "Ohne Quellen weiter"}</button></Footer>
    </section>
  );
}
