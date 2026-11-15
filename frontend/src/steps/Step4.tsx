import { useEffect, useState } from "react";
import { api, type Charter, type Project } from "../api";
import type { StepProps } from "../App";
import { Busy, ErrorNote, Footer, ManualBox, StepHeader, useAction, useManual } from "../ui";

function move<T>(list: T[], from: number, to: number): T[] {
  if (to < 0 || to >= list.length) return list;
  const copy = [...list];
  copy.splice(to, 0, copy.splice(from, 1)[0]);
  return copy;
}

export default function Step4({ project, setProject, next }: StepProps) {
  const [draft, setDraft] = useState<Charter | undefined>(project.charter);
  const [dirty, setDirty] = useState(false);
  const gen = useAction();
  const save = useAction();
  const manual = useManual();
  const [redo, setRedo] = useState(false);
  useEffect(() => { setDraft(project.charter); setDirty(false); }, [project.charter]);

  const edit = (changes: Partial<Charter>) => { setDraft((d) => (d ? { ...d, ...changes } : d)); setDirty(true); };
  const hasText = Object.values(project.contents).some((c) => c.markdown);

  const generate = () => {
    if (manual) { setRedo((r) => !r); return; }
    if (project.charter && !confirm(hasText
      ? "Die Struktur neu zu generieren verwirft die aktuelle Struktur und alle bereits geschriebenen Texte. Fortfahren?"
      : "Die aktuelle Struktur wird ersetzt. Fortfahren?")) return;
    gen.run(async () => setProject(await api<Project>("POST", `/projects/${project.id}/charter`)));
  };
  const persist = async () => {
    if (!draft || !dirty) return true;
    return save.run(async () => setProject(await api<Project>("PUT", `/projects/${project.id}/charter`, draft)));
  };
  const valid = !!draft && !!draft.title.trim() && draft.chapters.length > 0 && draft.chapters.every((c) => c.title.trim()) && draft.bonuses.every((b) => b.title.trim());

  return (
    <section>
      <StepHeader title="Product Charter und Struktur" lead="Titel, Preis und Inhaltsverzeichnis. Passe alles an, bevor geschrieben wird: Kapitel umbenennen, verschieben, ergänzen oder löschen.">
        {(!manual || draft) && (
          <button className={draft ? "btn-secondary" : "btn-primary"} disabled={gen.busy || project.generating} onClick={generate}>
            {gen.busy ? <Busy>Entwerfe Struktur</Busy> : draft ? "Neu generieren" : "Struktur generieren"}
          </button>
        )}
      </StepHeader>
      <ErrorNote message={gen.error} />
      {manual && (!draft || redo) && !project.generating && (
        <div className="mb-6">
          <ManualBox title={draft ? "Struktur neu erstellen (ersetzt die aktuelle Struktur und bereits geschriebene Texte)" : "Titel, Kapitel und Boni entwerfen"}
            getPrompt={async () => (await api<{ prompt: string }>("POST", `/projects/${project.id}/prompt`, { kind: "charter" })).prompt}
            onSubmit={async (answer) => { setProject(await api<Project>("POST", `/projects/${project.id}/charter`, { manual: answer })); setRedo(false); }} />
        </div>
      )}
      {project.generating && <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">Gerade wird geschrieben. Die Struktur kann erst danach geändert werden.</p>}

      {!draft && !gen.busy && !manual && <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-500">Noch keine Struktur. Klicke auf „Struktur generieren".</p>}

      {draft && (
        <fieldset disabled={project.generating} className="space-y-6">
          <div className="card grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="label" htmlFor="c-title">Titel</label>
              <input id="c-title" className="input text-lg font-bold" value={draft.title} onChange={(e) => edit({ title: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="c-sub">Untertitel</label>
              <input id="c-sub" className="input" value={draft.subtitle} onChange={(e) => edit({ subtitle: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-price">Zielpreis</label>
              <input id="c-price" className="input" value={draft.target_price} onChange={(e) => edit({ target_price: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-time">Geschätzte Lesezeit</label>
              <input id="c-time" className="input" value={draft.reading_time} onChange={(e) => edit({ reading_time: e.target.value })} />
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Kapitel ({draft.chapters.length})</h3>
            <ol className="space-y-3">
              {draft.chapters.map((ch, i) => {
                const set = (changes: Partial<typeof ch>) => edit({ chapters: draft.chapters.map((c, j) => (j === i ? { ...c, ...changes } : c)) });
                return (
                  <li key={ch.id || `new-${i}`} className="card p-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-1.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{i + 1}</span>
                      <div className="min-w-0 flex-1 space-y-2">
                        <input aria-label={`Titel Kapitel ${i + 1}`} className="input font-semibold" placeholder="Kapiteltitel" value={ch.title} onChange={(e) => set({ title: e.target.value })} />
                        <input aria-label={`Ziel Kapitel ${i + 1}`} className="input text-slate-600" placeholder="Was kann der Leser danach?" value={ch.summary} onChange={(e) => set({ summary: e.target.value })} />
                        <div>
                          <label className="label" htmlFor={`sec-${i}`}>Unterkapitel (eines pro Zeile)</label>
                          <textarea id={`sec-${i}`} rows={Math.max(3, ch.sections.length + 1)} className="input" value={ch.sections.join("\n")} onChange={(e) => set({ sections: e.target.value.split("\n") })} />
                        </div>
                      </div>
                      <div className="flex shrink-0 flex-col">
                        <button type="button" className="btn-ghost" aria-label={`Kapitel ${i + 1} nach oben`} disabled={i === 0} onClick={() => edit({ chapters: move(draft.chapters, i, i - 1) })}>↑</button>
                        <button type="button" className="btn-ghost" aria-label={`Kapitel ${i + 1} nach unten`} disabled={i === draft.chapters.length - 1} onClick={() => edit({ chapters: move(draft.chapters, i, i + 1) })}>↓</button>
                        <button type="button" className="btn-danger" aria-label={`Kapitel ${i + 1} löschen`} disabled={draft.chapters.length === 1}
                          onClick={() => { if (!project.contents[ch.id]?.markdown || confirm("Dieses Kapitel hat bereits Text. Trotzdem löschen?")) edit({ chapters: draft.chapters.filter((_, j) => j !== i) }); }}>✕</button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
            <button type="button" className="btn-secondary mt-3" onClick={() => edit({ chapters: [...draft.chapters, { id: "", title: "", summary: "", sections: [] }] })}>+ Kapitel hinzufügen</button>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Boni ({draft.bonuses.length})</h3>
            <ul className="space-y-3">
              {draft.bonuses.map((b, i) => {
                const set = (changes: Partial<typeof b>) => edit({ bonuses: draft.bonuses.map((x, j) => (j === i ? { ...x, ...changes } : x)) });
                return (
                  <li key={b.id || `new-${i}`} className="card flex items-start gap-3 p-4">
                    <span className="mt-1.5 shrink-0 rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800">B{i + 1}</span>
                    <div className="min-w-0 flex-1 space-y-2">
                      <input aria-label={`Titel Bonus ${i + 1}`} className="input font-semibold" placeholder="Bonustitel" value={b.title} onChange={(e) => set({ title: e.target.value })} />
                      <input aria-label={`Beschreibung Bonus ${i + 1}`} className="input text-slate-600" placeholder="Was enthält der Bonus?" value={b.description} onChange={(e) => set({ description: e.target.value })} />
                    </div>
                    <button type="button" className="btn-danger shrink-0" aria-label={`Bonus ${i + 1} löschen`} onClick={() => edit({ bonuses: draft.bonuses.filter((_, j) => j !== i) })}>✕</button>
                  </li>
                );
              })}
            </ul>
            <button type="button" className="btn-secondary mt-3" onClick={() => edit({ bonuses: [...draft.bonuses, { id: "", title: "", description: "" }] })}>+ Bonus hinzufügen</button>
          </div>
        </fieldset>
      )}

      <div className="mt-4"><ErrorNote message={save.error} /></div>
      <Footer>
        {dirty && !valid && <span className="text-sm text-rose-700">Jedes Kapitel und jeder Bonus braucht einen Titel.</span>}
        {dirty && <button className="btn-secondary" disabled={save.busy || !valid} onClick={persist}>{save.busy ? <Busy>Speichere</Busy> : "Änderungen speichern"}</button>}
        {!dirty && draft && <span className="text-sm text-slate-500">Gespeichert</span>}
        <button className="btn-primary" disabled={!draft || !valid || save.busy} onClick={async () => { if (await persist()) next(); }}>Weiter zum Schreiben</button>
      </Footer>
    </section>
  );
}
