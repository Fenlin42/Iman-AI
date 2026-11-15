import { useState } from "react";
import { api, type Concept, type Project, type State } from "../api";
import type { StepProps } from "../App";
import { Busy, ErrorNote, Footer, StepHeader, useAction } from "../ui";

function StateCard({ label, state, tone }: { label: string; state: State; tone: "before" | "after" }) {
  const c = tone === "before" ? "border-rose-200 bg-rose-50/60" : "border-emerald-200 bg-emerald-50/60";
  const chip = tone === "before" ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800";
  return (
    <div className={`rounded-xl border p-5 ${c}`}>
      <p className="label">{label}</p>
      <h4 className="text-lg font-bold leading-snug">{state.headline}</h4>
      <p className="mt-2 text-sm text-slate-700">{state.situation}</p>
      <ul className="mt-3 flex flex-wrap gap-1.5">
        {state.feelings.map((f) => <li key={f} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${chip}`}>{f}</li>)}
      </ul>
      <p className="mt-3 border-t border-black/5 pt-3 text-sm italic text-slate-600">{state.daily_reality}</p>
    </div>
  );
}

export default function Step2({ project, setProject, next }: StepProps) {
  const concepts = useAction();
  const map = useAction();
  const [pending, setPending] = useState("");
  const t = project.transformation;

  const loadConcepts = () => concepts.run(async () => setProject(await api<Project>("POST", `/projects/${project.id}/concepts`)));
  const choose = (concept: Concept) => {
    if (project.charter && project.concept?.name !== concept.name &&
        !confirm("Die Struktur in Schritt 4 basiert auf dem bisherigen Konzept und sollte danach neu generiert werden. Fortfahren?")) return;
    setPending(concept.name);
    map.run(async () => setProject(await api<Project>("POST", `/projects/${project.id}/transformation`, { concept }))).finally(() => setPending(""));
  };

  return (
    <section>
      <StepHeader title="Transformation Map" lead="Erst das Produktformat wählen, dann den Weg des Kunden vom Vorher zum Nachher sichtbar machen.">
        <div className="max-w-xs rounded-lg bg-brand-50 px-3 py-2 text-sm"><span className="label mb-0">Deine Nische</span>{project.uvz?.name}</div>
      </StepHeader>

      {!project.concepts ? (
        <div className="card text-center">
          <p className="mb-4 text-slate-600">Lass dir fünf Produktkonzepte mit Preisempfehlung vorschlagen.</p>
          <button className="btn-primary" disabled={concepts.busy} onClick={loadConcepts}>{concepts.busy ? <Busy>Entwickle Konzepte</Busy> : "Konzepte generieren"}</button>
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Wähle ein Konzept</h3>
            <button className="btn-ghost" disabled={concepts.busy || map.busy} onClick={loadConcepts}>{concepts.busy ? <Busy>Lädt</Busy> : "Andere Konzepte"}</button>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {project.concepts.map((c, i) => {
              const selected = project.concept?.name === c.name;
              return (
                <button key={i} onClick={() => choose(c)} disabled={map.busy} aria-pressed={selected}
                  className={`card flex flex-col text-left transition hover:shadow-md ${selected ? "border-brand-600 ring-2 ring-brand-600" : ""}`}>
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold leading-snug">{c.name}</span>
                    <span className="shrink-0 rounded-lg bg-slate-900 px-2.5 py-1 text-sm font-bold text-white">{c.price}</span>
                  </div>
                  <span className="mt-1 text-xs font-semibold uppercase tracking-wide text-brand-600">{c.format} · {c.duration}</span>
                  <p className="mt-2 text-sm text-slate-700">{c.promise}</p>
                  <p className="mt-auto pt-3 text-xs text-slate-500">{c.price_reasoning}</p>
                  {pending === c.name && <span className="mt-3 text-sm font-medium text-brand-600"><Busy>Erstelle Transformation Map</Busy></span>}
                </button>
              );
            })}
          </div>
        </>
      )}
      <div className="mt-3 space-y-2"><ErrorNote message={concepts.error} /><ErrorNote message={map.error} /></div>

      {t && (
        <div className="mt-10">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Vorher und Nachher</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <StateCard label="Vorher" state={t.before} tone="before" />
            <StateCard label="Nachher" state={t.after} tone="after" />
          </div>
          <h3 className="mt-8 mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Meilensteine auf dem Weg</h3>
          <ol className="relative ml-3 space-y-5 border-l-2 border-brand-100 pl-7">
            {t.milestones.map((m, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[42px] grid h-7 w-7 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">{i + 1}</span>
                <div className="card p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="font-bold">{m.title}</h4>
                    <span className="text-xs font-semibold uppercase tracking-wide text-brand-600">{m.timeframe}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-700">{m.description}</p>
                  <p className="mt-2 text-sm"><span className="font-semibold">Ergebnis:</span> {m.outcome}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
      <Footer><button className="btn-primary" disabled={!t} onClick={next}>Weiter zum Wissen</button></Footer>
    </section>
  );
}
