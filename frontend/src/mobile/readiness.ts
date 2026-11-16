import { daysUntil, formatDate } from "../labels";
import { isOpen } from "../todo";
import type { OpenRow } from "../todo";
import type { Cell, CellStatus, Certification, MatrixRow, Member, Overview } from "../types";

export type MemberState = "critical" | "soon" | "ready";
export type Segment = "all" | "critical" | "soon";

const CRITICAL: ReadonlySet<CellStatus> = new Set(["missing", "expired"]);

export function isCritical(status: CellStatus): boolean {
  return CRITICAL.has(status);
}

/** Classifies a member. Missing or expired items make the member not ready, items about to expire are a warning. */
export function memberState(row: Pick<MatrixRow, "worst_status">): MemberState {
  if (isCritical(row.worst_status)) return "critical";
  return row.worst_status === "expiring" ? "soon" : "ready";
}

export interface Readiness {
  total: number;
  ready: number;
  soon: number;
  critical: number;
}

/** Counts how many members are ready. A member with items about to expire still counts as ready. */
export function readiness(rows: readonly Pick<MatrixRow, "worst_status">[]): Readiness {
  const out: Readiness = { total: rows.length, ready: 0, soon: 0, critical: 0 };
  for (const r of rows) {
    const s = memberState(r);
    if (s === "critical") out.critical += 1;
    else {
      out.ready += 1;
      if (s === "soon") out.soon += 1;
    }
  }
  return out;
}

/** Narrows open rows to one segment. Rows keep only the items that belong to the segment. */
export function segmentRows(rows: readonly OpenRow[], segment: Segment): OpenRow[] {
  if (segment === "all") return [...rows];
  const keep = (c: Cell) => (segment === "critical" ? isCritical(c.status) : c.status === "expiring");
  return rows.map((r) => ({ ...r, open: r.open.filter(keep) })).filter((r) => r.open.length > 0);
}

/** Counts the members per segment. */
export function segmentCounts(rows: readonly OpenRow[]): Record<Segment, number> {
  return {
    all: rows.length,
    critical: segmentRows(rows, "critical").length,
    soon: segmentRows(rows, "soon").length,
  };
}

export interface CertStat {
  certification: Certification;
  required: number;
  valid: number;
  expiring: number;
  expired: number;
  missing: number;
}

/**
 * Aggregates the overview per certification. Only required cells count. Certifications with the most missing or
 * expired items come first, then those with items about to expire, then the catalog order.
 */
export function certStats(overview: Pick<Overview, "certifications" | "rows">): CertStat[] {
  const stats = overview.certifications.map<CertStat>((c) => ({
    certification: c,
    required: 0,
    valid: 0,
    expiring: 0,
    expired: 0,
    missing: 0,
  }));
  const byId = new Map(stats.map((s) => [s.certification.id, s]));
  for (const row of overview.rows) {
    for (const cell of row.cells) {
      const s = byId.get(cell.certification_id);
      if (!s || !cell.required || cell.status === "not_required") continue;
      s.required += 1;
      s[cell.status] += 1;
    }
  }
  return stats
    .map((s, i) => ({ s, i }))
    .sort((a, b) => b.s.missing + b.s.expired - (a.s.missing + a.s.expired) || b.s.expiring - a.s.expiring || a.i - b.i)
    .map(({ s }) => s);
}

export interface StatusGroup {
  status: CellStatus;
  entries: { member: Member; cell: Cell }[];
}

const GROUP_ORDER: CellStatus[] = ["missing", "expired", "expiring", "valid", "not_required"];

function byName(a: Member, b: Member): number {
  return a.last_name.localeCompare(b.last_name, "de") || a.first_name.localeCompare(b.first_name, "de");
}

/**
 * Groups the members of an overview by their status for one certification. Expiring entries are ordered by the expiry
 * date, all other groups by name. Empty groups are left out.
 */
export function groupByStatus(overview: Pick<Overview, "rows">, certificationId: number): StatusGroup[] {
  const groups = new Map<CellStatus, StatusGroup>(GROUP_ORDER.map((s) => [s, { status: s, entries: [] }]));
  for (const row of overview.rows) {
    const cell = row.cells.find((c) => c.certification_id === certificationId);
    if (cell) groups.get(cell.status)!.entries.push({ member: row.member, cell });
  }
  for (const g of groups.values()) {
    g.entries.sort((a, b) =>
      g.status === "expiring"
        ? (a.cell.expires_on ?? "").localeCompare(b.cell.expires_on ?? "") || byName(a.member, b.member)
        : byName(a.member, b.member),
    );
  }
  return GROUP_ORDER.map((s) => groups.get(s)!).filter((g) => g.entries.length > 0);
}

/** Returns the index letter of a name. Umlauts use their base letter, anything that is not a letter becomes a hash. */
export function indexLetter(name: string): string {
  const first = name.trim().charAt(0).normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
  return /^[A-Z]$/.test(first) ? first : "#";
}

export interface LetterGroup<T> {
  letter: string;
  items: T[];
}

/** Sorts members by name and groups them by the first letter of the last name. */
export function groupByLetter<T extends { member: Member }>(items: readonly T[]): LetterGroup<T>[] {
  const sorted = [...items].sort((a, b) => byName(a.member, b.member));
  const out: LetterGroup<T>[] = [];
  for (const item of sorted) {
    const letter = indexLetter(item.member.last_name);
    const last = out[out.length - 1];
    if (last && last.letter === letter) last.items.push(item);
    else out.push({ letter, items: [item] });
  }
  return out;
}

export function initials(m: Pick<Member, "first_name" | "last_name">): string {
  return `${m.first_name.trim().charAt(0)}${m.last_name.trim().charAt(0)}`.toUpperCase() || "?";
}

function span(days: number): string {
  if (days === 1) return "1 Tag";
  if (days < 45) return `${days} Tagen`;
  const months = Math.round(days / 30.4);
  if (months < 18) return months === 1 ? "1 Monat" : `${months} Monaten`;
  const years = Math.round(days / 365);
  return years === 1 ? "1 Jahr" : `${years} Jahren`;
}

/** Describes a cell in a full sentence fragment for lists on small screens. */
export function dueText(cell: Pick<Cell, "status" | "expires_on" | "completed_on">, today: string): string {
  const days = daysUntil(cell.expires_on, today);
  switch (cell.status) {
    case "missing":
      return "Fehlt";
    case "expired":
      return days === null ? "Abgelaufen" : `Abgelaufen seit ${span(-days)}`;
    case "expiring":
      if (days === null || days <= 0) return "Läuft heute ab";
      return days === 1 ? "Läuft morgen ab" : `Läuft in ${span(days)} ab`;
    case "valid":
      return cell.expires_on ? `Gültig bis ${formatDate(cell.expires_on)}` : "Unbefristet gültig";
    default:
      return cell.completed_on ? `Zuletzt ${formatDate(cell.completed_on)}` : "Nicht gefordert";
  }
}

/** Counts open items of a row. */
export function openCount(row: Pick<MatrixRow, "cells">): number {
  return row.cells.filter((c) => isOpen(c.status)).length;
}

export const RECENT_KEY = "einsatzbereit.recentCertifications";
const RECENT_MAX = 4;

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function browserStorage(): StorageLike | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Reads the ids of recently recorded certifications, newest first. */
export function readRecent(storage: StorageLike | null = browserStorage()): number[] {
  try {
    const parsed: unknown = JSON.parse(storage?.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((v): v is number => Number.isInteger(v)).slice(0, RECENT_MAX) : [];
  } catch {
    return [];
  }
}

/** Moves a certification to the front of the recent list. */
export function rememberRecent(id: number, storage: StorageLike | null = browserStorage()): number[] {
  const next = [id, ...readRecent(storage).filter((x) => x !== id)].slice(0, RECENT_MAX);
  try {
    storage?.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    return next;
  }
  return next;
}

/** Splits certifications into recently used ones in recent order and the rest in catalog order. */
export function splitRecent<T extends { id: number }>(items: readonly T[], recent: readonly number[]) {
  const byId = new Map(items.map((c) => [c.id, c]));
  const top = recent.map((id) => byId.get(id)).filter((c): c is T => c !== undefined);
  const ids = new Set(top.map((c) => c.id));
  return { recent: top, rest: items.filter((c) => !ids.has(c.id)) };
}

/** Parses a comma separated id list from the URL. Invalid parts are dropped. */
export function parseIds(raw: unknown): number[] {
  const v = Array.isArray(raw) ? raw[0] : raw;
  if (typeof v !== "string") return [];
  return [
    ...new Set(
      v
        .split(",")
        .filter((p) => /^\d+$/.test(p))
        .map(Number),
    ),
  ];
}

/** Describes the validity rule of a certification in plain words, written to follow the kind after a comma. */
export function validityText(c: Pick<Certification, "validity_mode" | "validity_months">): string {
  const n = c.validity_months;
  const months = n === 1 ? "1 Monat" : `${n} Monate`;
  switch (c.validity_mode) {
    case "fixed_duration":
      return n ? `gilt ${months} ab Abschluss` : "unbefristet";
    case "end_of_year":
      return n ? `gilt ${months}, dann bis Jahresende` : "unbefristet";
    case "manual":
      return "Ablaufdatum je Eintrag";
    default:
      return "unbefristet";
  }
}
