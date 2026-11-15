import { type ReactNode, useCallback, useState } from "react";

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
