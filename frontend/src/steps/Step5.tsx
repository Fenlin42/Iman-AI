import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Content, type Project } from "../api";
import type { StepProps } from "../App";
import { Busy, ErrorNote, StepHeader, useAction } from "../ui";

const ACCENTS = [
  { id: "indigo", color: "#4338ca", name: "Indigo" },
  { id: "emerald", color: "#047857", name: "Smaragd" },
  { id: "rose", color: "#be123c", name: "Rot" },
  { id: "amber", color: "#b45309", name: "Bernstein" },
  { id: "slate", color: "#334155", name: "Schiefer" },
];
const STATUS: Record<Content["status"], [string, string]> = {
  pending: ["Offen", "bg-slate-100 text-slate-600"],
  queued: ["Wartet", "bg-slate-100 text-slate-600"],
  running: ["Schreibt", "bg-brand-100 text-brand-700"],
  done: ["Fertig", "bg-emerald-100 text-emerald-800"],
  error: ["Fehler", "bg-rose-100 text-rose-800"],
};
const words = (s: string) => (s.trim() ? s.trim().split(/\s+/).length : 0);

export default function Step5({ project, setProject }: StepProps) {
  const pid = project.id;
  const charter = project.charter!;
  const items = [
    ...charter.chapters.map((c, i) => ({ id: c.id, label: `Kapitel ${i + 1}`, title: c.title })),
    ...charter.bonuses.map((b, i) => ({ id: b.id, label: `Bonus ${i + 1}`, title: b.title })),
  ];
  const [tab, setTab] = useState<"write" | "preview">("write");
  const [live, setLive] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState(items[0]?.id ?? "");
  const [editing, setEditing] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");
  const [previewKey, setPreviewKey] = useState(0);
  const [design, setDesign] = useState(project.design ?? { author: "", accent: "indigo" });
  const act = useAction();
  const pdf = useAction();
  const liveBox = useRef<HTMLPreElement>(null);

  const refresh = useCallback(async () => setProject(await api<Project>("GET", `/projects/${pid}`)), [pid, setProject]);

  // Live events while the server writes.
  useEffect(() => {
    const source = new EventSource(`/api/projects/${pid}/events`);
    source.onmessage = (msg) => {
      const e = JSON.parse(msg.data);
      if (e.type === "start") { setLive((l) => ({ ...l, [e.item_id]: "" })); setSelected(e.item_id); refresh(); }
      else if (e.type === "delta") setLive((l) => ({ ...l, [e.item_id]: (l[e.item_id] ?? "") + e.text }));
      else if (e.type === "error") { act.setError(e.message); refresh(); }
      else { refresh(); if (e.type === "finished") setPreviewKey((k) => k + 1); }
    };
    return () => source.close();
  }, [pid, refresh, act.setError]);

  // After a reload mid-run the stream only delivers new chunks; poll so stored progress still shows.
  useEffect(() => {
    if (!project.generating) return;
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [project.generating, refresh]);

  useEffect(() => { liveBox.current?.scrollTo({ top: liveBox.current.scrollHeight }); }, [live, selected]);

  const content = (id: string): Content => project.contents[id] ?? { markdown: "", status: "pending", error: "" };
  const textOf = (id: string) => {
    const c = content(id);
    const streamed = live[id] ?? "";
    return c.status === "running" && streamed.length > c.markdown.length ? streamed : c.markdown;
  };
  const done = items.filter((i) => content(i.id).status === "done").length;
  const allDone = done === items.length && items.length > 0;
  const totalWords = items.reduce((n, i) => n + words(textOf(i.id)), 0);
  const current = items.find((i) => i.id === selected) ?? items[0];

  const generate = (item_ids?: string[], extra = "") => act.run(async () => {
    setProject(await api<Project>("POST", `/projects/${pid}/generate`, { item_ids: item_ids ?? null, instruction: extra }));
  });
  const saveDesign = (next: typeof design) => {
    setDesign(next);
    api<Project>("PUT", `/projects/${pid}/design`, next).then((p) => { setProject(p); setPreviewKey((k) => k + 1); }).catch((e) => act.setError(e.message));
  };
  const download = () => pdf.run(async () => {
    const res = await fetch(`/api/projects/${pid}/pdf`);
    if (!res.ok) throw new Error("PDF konnte nicht erzeugt werden.");
    const name = res.headers.get("content-disposition")?.match(/filename="(.+?)"/)?.[1] ?? "produkt.pdf";
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    a.click();
    URL.revokeObjectURL(url);
  });

  return (
    <section>
      <StepHeader title="Produkt schreiben, prüfen, exportieren" lead="Erst wird Kapitel für Kapitel geschrieben. Danach liest du das fertige Produkt in der Vorschau. Wenn es dir gefällt, lädst du es als PDF herunter.">
        <div className="text-right text-sm text-slate-600">
          <div className="font-semibold text-ink">{done} von {items.length} Teilen fertig</div>
          <div>{totalWords.toLocaleString("de-DE")} Wörter</div>
        </div>
      </StepHeader>

      <div className="mb-5 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuemin={0} aria-valuemax={items.length} aria-valuenow={done} aria-label="Fortschritt">
        <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${items.length ? (done / items.length) * 100 : 0}%` }} />
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        {project.generating ? (
          <>
            <span className="font-medium text-brand-700"><Busy>Schreibt gerade. Du kannst die Seite offen lassen oder später zurückkommen.</Busy></span>
            <button className="btn-secondary" onClick={() => act.run(async () => setProject(await api<Project>("POST", `/projects/${pid}/cancel`)))}>Abbrechen</button>
          </>
        ) : !allDone ? (
          <button className="btn-primary" disabled={act.busy} onClick={() => generate()}>
            {done === 0 ? "Komplettes Produkt schreiben" : `Fehlende ${items.length - done} Teile schreiben`}
          </button>
        ) : (
          <span className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">Alles geschrieben. Sieh dir die Vorschau an.</span>
        )}
        <div className="ml-auto flex rounded-lg border border-slate-300 bg-white p-0.5" role="tablist">
          {(["write", "preview"] as const).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => { setTab(t); if (t === "preview") setPreviewKey((k) => k + 1); }}
              className={`rounded-md px-4 py-1.5 text-sm font-semibold ${tab === t ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>
              {t === "write" ? "Schreiben" : "Vorschau & PDF"}
            </button>
          ))}
        </div>
      </div>
      <div className="mb-4"><ErrorNote message={act.error} /></div>

      {tab === "write" && current && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
          <ol className="space-y-1.5">
            {items.map((item) => {
              const c = content(item.id);
              const [label, cls] = STATUS[c.status];
              return (
                <li key={item.id}>
                  <button onClick={() => { setSelected(item.id); setEditing(null); }} aria-current={item.id === current.id}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${item.id === current.id ? "border-brand-600 bg-white shadow-sm" : "border-transparent hover:bg-white"}`}>
                    <span className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.label}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>
                    </span>
                    <span className="mt-0.5 block truncate text-sm font-medium">{item.title}</span>
                  </button>
                </li>
              );
            })}
          </ol>

          <div className="card min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="label mb-0">{current.label} · {words(textOf(current.id)).toLocaleString("de-DE")} Wörter</p>
                <h3 className="text-lg font-bold">{current.title}</h3>
              </div>
              {!project.generating && content(current.id).markdown && editing === null && (
                <button className="btn-secondary" onClick={() => setEditing(content(current.id).markdown)}>Text bearbeiten</button>
              )}
            </div>
            {content(current.id).status === "error" && <div className="mt-3"><ErrorNote message={content(current.id).error || "Fehler beim Schreiben."} /></div>}

            {editing !== null ? (
              <div className="mt-4">
                <label className="label" htmlFor="md-edit">Markdown</label>
                <textarea id="md-edit" rows={22} className="input font-mono text-[13px] leading-relaxed" value={editing} onChange={(e) => setEditing(e.target.value)} />
                <div className="mt-3 flex justify-end gap-2">
                  <button className="btn-secondary" onClick={() => setEditing(null)}>Verwerfen</button>
                  <button className="btn-primary" disabled={act.busy} onClick={() => act.run(async () => {
                    setProject(await api<Project>("PUT", `/projects/${pid}/contents/${current.id}`, { markdown: editing }));
                    setEditing(null);
                  })}>Speichern</button>
                </div>
              </div>
            ) : textOf(current.id) ? (
              <pre ref={liveBox} className="mt-4 max-h-[520px] overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-800">{textOf(current.id)}</pre>
            ) : (
              <p className="mt-4 rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">Noch nicht geschrieben.</p>
            )}

            {!project.generating && editing === null && (
              <div className="mt-4 border-t border-slate-200 pt-4">
                <label className="label" htmlFor="instr">Wunsch für diesen Teil (optional)</label>
                <div className="flex flex-wrap gap-2">
                  <input id="instr" className="input min-w-0 flex-1" placeholder="z. B. mehr Beispiele für Einzelpraxen, kürzer, konkretere Skripte" value={instruction} onChange={(e) => setInstruction(e.target.value)} />
                  <button className="btn-secondary" disabled={act.busy} onClick={() => {
                    if (!content(current.id).markdown || confirm("Der aktuelle Text dieses Teils wird ersetzt. Fortfahren?")) generate([current.id], instruction).then(() => setInstruction(""));
                  }}>{content(current.id).markdown ? "Neu schreiben" : "Diesen Teil schreiben"}</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "preview" && (
        <div>
          <div className="card mb-4 flex flex-wrap items-end gap-5">
            <div className="min-w-48 flex-1">
              <label className="label" htmlFor="author">Autor auf dem Deckblatt</label>
              <input id="author" className="input" placeholder="Dein Name" defaultValue={design.author} onBlur={(e) => e.target.value !== design.author && saveDesign({ ...design, author: e.target.value })} />
            </div>
            <div>
              <span className="label">Akzentfarbe</span>
              <div className="flex gap-2" role="radiogroup" aria-label="Akzentfarbe">
                {ACCENTS.map((a) => (
                  <button key={a.id} role="radio" aria-checked={design.accent === a.id} aria-label={a.name} title={a.name} onClick={() => saveDesign({ ...design, accent: a.id })}
                    className={`h-9 w-9 rounded-full border-2 border-white ring-2 ${design.accent === a.id ? "ring-slate-900" : "ring-transparent"}`} style={{ background: a.color }} />
                ))}
              </div>
            </div>
            <div className="text-right">
              <button className="btn-primary px-5 py-2.5" disabled={pdf.busy || done === 0} onClick={download}>{pdf.busy ? <Busy>Erzeuge PDF</Busy> : "Als PDF herunterladen"}</button>
              {!allDone && done > 0 && <p className="mt-1 text-xs text-amber-700">Noch nicht alle Teile sind geschrieben.</p>}
            </div>
          </div>
          <ErrorNote message={pdf.error} />
          <p className="mb-2 text-sm text-slate-500">So sieht dein Produkt aus. Im PDF kommen Seitenzahlen, Kopfzeilen und Seitenzahlen im Inhaltsverzeichnis dazu.</p>
          <iframe key={previewKey} title="Vorschau des Produkts" sandbox="" src={`/api/projects/${pid}/preview?v=${previewKey}`}
            className="h-[80vh] w-full rounded-xl border border-slate-300 bg-slate-200" />
        </div>
      )}
    </section>
  );
}
