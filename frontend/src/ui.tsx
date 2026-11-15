import { createContext, type ReactNode, useCallback, useContext, useState } from "react";

/** Runs an async action and tracks loading + error for it. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return false;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, run, setError };
}

export function ErrorNote({ message }: { message: string }) {
  if (!message) return null;
  return <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{message}</p>;
}

export function Busy({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center gap-2"><span className="spinner" />{children}</span>;
}

export function StepHeader({ title, lead, children }: { title: string; lead: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        <p className="mt-1 text-slate-600">{lead}</p>
      </div>
      {children}
    </div>
  );
}

export function Footer({ children }: { children: ReactNode }) {
  return <div className="mt-8 flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 pt-5">{children}</div>;
}

/** Copy mode: texts come from the user's own Claude chat instead of the API. */
export const ModeContext = createContext(false);
export const useManual = () => useContext(ModeContext);

export function ManualBox({ title, getPrompt, onSubmit, disabled, disabledHint, submitLabel = "Antwort übernehmen" }: {
  title: string;
  getPrompt: () => Promise<string>;
  onSubmit: (answer: string) => Promise<unknown>;
  disabled?: boolean;
  disabledHint?: string;
  submitLabel?: string;
}) {
  const [prompt, setPrompt] = useState("");
  const [copied, setCopied] = useState(false);
  const [answer, setAnswer] = useState("");
  const copy = useAction();
  const submit = useAction();

  const doCopy = () => copy.run(async () => {
    const text = await getPrompt();
    setPrompt(text);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false); // the prompt is shown below for copying by hand
    }
  });

  return (
    <div className="rounded-xl border-2 border-dashed border-brand-500/50 bg-brand-50/50 p-4">
      <p className="mb-3 font-semibold">{title}</p>
      <ol className="space-y-4 text-sm">
        <li>
          <p className="mb-2 font-medium"><span className="mr-2 inline-grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">1</span>Prompt kopieren und in einem neuen Claude-Chat einfügen</p>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn-primary" disabled={disabled || copy.busy} onClick={doCopy}>{copy.busy ? <Busy>Erstelle Prompt</Busy> : copied ? "Kopiert ✓ (erneut kopieren)" : "Prompt kopieren"}</button>
            <a className="btn-secondary" href="https://claude.ai/new" target="_blank" rel="noreferrer">claude.ai öffnen ↗</a>
            {disabled && disabledHint && <span className="text-slate-500">{disabledHint}</span>}
          </div>
          {prompt && !copied && (
            <div className="mt-2">
              <label className="label">Automatisches Kopieren nicht möglich. Bitte hier alles markieren und kopieren:</label>
              <textarea readOnly rows={5} className="input font-mono text-xs" value={prompt} onFocus={(e) => e.target.select()} />
            </div>
          )}
          <div className="mt-2"><ErrorNote message={copy.error} /></div>
        </li>
        <li>
          <p className="mb-2 font-medium"><span className="mr-2 inline-grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">2</span>Antwort von Claude kopieren und hier einfügen</p>
          <textarea aria-label={`Antwort einfügen: ${title}`} rows={5} className="input font-mono text-xs" placeholder="Komplette Antwort hier einfügen …" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <button type="button" className="btn-primary" disabled={disabled || submit.busy || answer.trim().length < 20}
              onClick={() => submit.run(async () => { await onSubmit(answer); setAnswer(""); setCopied(false); setPrompt(""); })}>
              {submit.busy ? <Busy>Übernehme</Busy> : submitLabel}
            </button>
          </div>
          <div className="mt-2"><ErrorNote message={submit.error} /></div>
        </li>
      </ol>
    </div>
  );
}
