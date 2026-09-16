import type { CellStatus, CertificationKind, ValidityMode } from "./types";

export const STATUS_LABEL: Record<CellStatus, string> = {
  missing: "Fehlt",
  expired: "Abgelaufen",
  expiring: "Läuft bald ab",
  valid: "Gültig",
  not_required: "Nicht gefordert",
};

export const KIND_LABEL: Record<CertificationKind, string> = {
  seminar: "Seminar",
  exercise: "Übung",
  test: "Test",
  training: "Weiterbildung",
};

export const VALIDITY_LABEL: Record<ValidityMode, string> = {
  unlimited: "Unbefristet",
  fixed_duration: "Feste Dauer ab Abschluss",
  end_of_year: "Bis Jahresende nach Dauer",
  manual: "Ablaufdatum pro Eintrag",
};

export function formatDate(iso: string | null): string {
  if (!iso) return "–";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

/** Whole days between two calendar dates (YYYY-MM-DD). Independent of time zone and DST. */
export function daysUntil(iso: string | null, today: string): number | null {
  if (!iso) return null;
  return Math.round((Date.parse(iso.slice(0, 10)) - Date.parse(today.slice(0, 10))) / 86_400_000);
}

export function shortName(name: string, short: string): string {
  if (short) return short;
  const words = name.split(/[\s-]+/).filter(Boolean);
  return words.length > 1 ? words.map((w) => w[0]).join("").slice(0, 4).toUpperCase() : name.slice(0, 4);
}

export function cellHint(status: CellStatus, expires: string | null, today: string): string {
  if (status === "missing") return "fehlt";
  if (status === "not_required") return expires ? formatDate(expires) : "";
  if (!expires) return "unbefristet";
  const days = daysUntil(expires, today) ?? 0;
  if (status === "expired") return `seit ${formatDate(expires)}`;
  if (status === "expiring") return days === 0 ? "heute" : `noch ${days} T.`;
  return `bis ${formatDate(expires)}`;
}

const dateTimeFormat = new Intl.DateTimeFormat("de-DE", {
  timeZone: "Europe/Berlin",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Formats a server timestamp (UTC) in German local time. */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "–" : dateTimeFormat.format(d);
}
