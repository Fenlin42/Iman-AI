export type Niche = { name: string; problem: string; audience: string; willingness_to_pay: string; why_profitable: string; demand_signal?: string };
export type Concept = { name: string; format: string; promise: string; duration: string; price: string; price_reasoning: string };
export type State = { headline: string; situation: string; feelings: string[]; daily_reality: string };
export type Milestone = { title: string; timeframe: string; description: string; outcome: string };
export type Transformation = { before: State; after: State; milestones: Milestone[] };
export type Reference = { id: string; type: "note" | "url"; title: string; content: string; url?: string };
export type Chapter = { id: string; title: string; summary: string; sections: string[] };
export type Bonus = { id: string; title: string; description: string };
export type Charter = { title: string; subtitle: string; target_price: string; reading_time: string; chapters: Chapter[]; bonuses: Bonus[] };
export type Content = { markdown: string; status: "pending" | "queued" | "running" | "done" | "error"; error: string };
export type Project = {
  id: string; name: string; language: "de" | "en"; step: number;
  mode?: string; input?: string; niches?: Niche[]; uvz?: Niche;
  concepts?: Concept[]; concept?: Concept; transformation?: Transformation;
  references: Reference[]; charter?: Charter; design?: { author: string; accent: string };
  contents: Record<string, Content>; generating: boolean;
};
export type ProjectSummary = { id: string; name: string; step: number; title: string; updated_at: number };
export type Status = { auth_required: boolean; authenticated: boolean; has_key: boolean; mock: boolean; model: string };

/** Browser-side backups: on hosts without a persistent disk the server loses projects on restart. */
const BACKUP = "pw-backup-";
export const backups = {
  save(p: Project): boolean {
    try { localStorage.setItem(BACKUP + p.id, JSON.stringify(p)); return true; } catch { return false; }
  },
  remove(id: string) { try { localStorage.removeItem(BACKUP + id); } catch { /* nothing to remove */ } },
  all(): Project[] {
    const out: Project[] = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith(BACKUP)) out.push(JSON.parse(localStorage.getItem(key)!));
      }
    } catch { /* storage unavailable */ }
    return out;
  },
};

/** Puts back every backed-up project the server no longer has. Returns how many were restored. */
export async function restoreLost(known: string[]): Promise<number> {
  let n = 0;
  for (const p of backups.all()) {
    if (known.includes(p.id)) continue;
    try {
      if ((await api<{ restored: boolean }>("POST", "/projects/import", p)).restored) n++;
    } catch { /* a broken backup must not block the others */ }
  }
  return n;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Server nicht erreichbar.");
  }
  if (!res.ok) {
    let message = `Fehler ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = "Eingabe unvollständig oder ungültig.";
    } catch { /* keep the generic message */ }
    if (res.status === 401 && path !== "/login") window.dispatchEvent(new Event("pw-unauthorized"));
    throw new ApiError(res.status, message);
  }
  return res.json();
}
