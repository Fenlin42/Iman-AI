import { useState } from "react";
import { api, type Niche, type Project } from "../api";
import type { StepProps } from "../App";
import { Busy, ErrorNote, Footer, ManualBox, StepHeader, useAction, useManual } from "../ui";

const MODES = [
  { id: "explore", title: "Profitable Chancen finden", hint: "Du nennst Interessen, Skills oder ein grobes Thema und bekommst 10 spitze Mikro-Nischen.",
    placeholder: "z. B. Ich bin Physiotherapeutin, arbeite viel mit Läufern und mag Krafttraining …" },
  { id: "specific", title: "Konkrete Idee", hint: "Du hast schon ein Problem oder eine Produktidee und willst sie schärfen.",
    placeholder: "z. B. Ein Guide für Hobbyläufer über 40, die nach einer Knie-OP wieder 10 km laufen wollen …" },
];

export default function Step1({ project, setProject, next }: StepProps) {
  const [mode, setMode] = useState(project.mode ?? "explore");
  const [input, setInput] = useState(project.input ?? "");
  const { busy, error, run } = useAction();
  const manual = useManual();
  const current = MODES.find((m) => m.id === mode)!;

  const generate = () => run(async () => setProject(await api<Project>("POST", `/projects/${project.id}/niches`, { mode, input })));
  const choose = (niche: Niche) => {
    if (project.concept && project.uvz?.name !== niche.name &&
        !confirm("Eine andere Nische setzt Konzept und Transformation zurück. Fortfahren?")) return;
    run(async () => setProject(await api<Project>("POST", `/projects/${project.id}/uvz`, { niche })));
  };

  return (
    <section>
      <StepHeader title="Unique Value Zone finden" lead="Die Nische entscheidet, ob sich das Produkt verkauft. Je enger die Zielgruppe und je schmerzhafter das Problem, desto besser." />
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Modus">
        {MODES.map((m) => (
          <button key={m.id} role="radio" aria-checked={mode === m.id} onClick={() => setMode(m.id)}
            className={`rounded-xl border-2 p-4 text-left transition ${mode === m.id ? "border-brand-600 bg-brand-50" : "border-slate-200 bg-white hover:border-slate-300"}`}>
            <span className="block font-semibold">{m.title}</span>
            <span className="mt-1 block text-sm text-slate-600">{m.hint}</span>
          </button>
        ))}
      </div>
      <div className="mt-4">
        <label className="label" htmlFor="uvz-input">{mode === "explore" ? "Deine Interessen, Skills oder dein Thema" : "Dein Problem oder deine Produktidee"}</label>
        <textarea id="uvz-input" rows={4} className="input" placeholder={current.placeholder} value={input} onChange={(e) => setInput(e.target.value)} />
      </div>
      {manual ? (
        <div className="mt-3">
          <ManualBox title={mode === "explore" ? "10 Nischen finden" : "Idee schärfen"}
            disabled={input.trim().length < 3} disabledHint="Bitte zuerst oben etwas eingeben."
            getPrompt={async () => (await api<{ prompt: string }>("POST", `/projects/${project.id}/prompt`, { kind: "niches", mode, input })).prompt}
            onSubmit={async (answer) => setProject(await api<Project>("POST", `/projects/${project.id}/niches`, { mode, input, manual: answer }))} />
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button className="btn-primary" disabled={busy || input.trim().length < 3} onClick={generate}>
            {busy ? <Busy>Analysiere Markt</Busy> : project.niches ? "Neu generieren" : mode === "explore" ? "10 Nischen finden" : "Idee schärfen"}
          </button>
          {busy && <span className="text-sm text-slate-500">Das dauert meist 20 bis 60 Sekunden.</span>}
        </div>
      )}
      <div className="mt-3"><ErrorNote message={error} /></div>

      {project.niches && (
        <>
          <h3 className="mt-8 mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Wähle deine Nische per Klick</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {project.niches.map((n, i) => {
              const selected = project.uvz?.name === n.name;
              return (
                <button key={i} onClick={() => choose(n)} aria-pressed={selected} disabled={busy}
                  className={`card text-left transition hover:shadow-md ${selected ? "border-brand-600 ring-2 ring-brand-600" : ""}`}>
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-lg font-bold leading-snug">{n.name}</span>
                    {selected && <span className="shrink-0 rounded-full bg-brand-600 px-2.5 py-0.5 text-xs font-semibold text-white">Gewählt</span>}
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{n.problem}</p>
                  <dl className="mt-3 space-y-2 text-sm">
                    <div><dt className="label mb-0">Zielgruppe</dt><dd>{n.audience}</dd></div>
                    <div><dt className="label mb-0">Zahlungsbereitschaft (Schätzung)</dt><dd>{n.willingness_to_pay}</dd></div>
                    <div><dt className="label mb-0">Warum attraktiv</dt><dd className="text-slate-600">{n.why_profitable}</dd></div>
                  </dl>
                </button>
              );
            })}
          </div>
        </>
      )}
      <Footer><button className="btn-primary" disabled={!project.uvz} onClick={next}>Weiter zur Transformation</button></Footer>
    </section>
  );
}
