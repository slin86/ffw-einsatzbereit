import type { TokenResponse } from "./types";

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onAuthLost: (() => void) | null = null;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setAuthLostHandler(handler: () => void): void {
  onAuthLost = handler;
}

/** Exchanges the httpOnly refresh cookie for a new access token. Concurrent calls share one request. */
export function refreshAccessToken(): Promise<boolean> {
  refreshing ??= fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" })
    .then(async (r) => {
      if (!r.ok) return false;
      const body = (await r.json()) as TokenResponse;
      accessToken = body.access_token;
      return accessToken !== null;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers, credentials: "same-origin" });
  if (res.status === 401 && retry && !path.startsWith("/api/auth/")) {
    if (await refreshAccessToken()) return raw(path, init, false);
    accessToken = null;
    onAuthLost?.();
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
    if (typeof body.detail === "string") throw new ApiError(res.status, body.detail);
    if (Array.isArray(body.detail)) throw new ApiError(res.status, "Eingaben unvollständig oder ungültig");
    throw new ApiError(res.status, res.statusText);
  }
  return res;
}

export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await raw(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204 || res.status === 202) return undefined as T;
  return (await res.json()) as T;
}

export async function download(path: string): Promise<void> {
  const res = await raw(path);
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "export";
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const GONE = "Nicht mehr vorhanden. Lade die Seite neu, vielleicht wurde es inzwischen gelöscht.";
const STALE = "Die Seite ist nicht mehr aktuell. Lade sie neu und versuche es noch einmal.";

export const ERROR_TEXT: Readonly<Record<string, string>> = {
  "Invalid credentials": "E-Mail, Passwort oder Code stimmen nicht.",
  "Not authenticated": "Du bist nicht mehr angemeldet.",
  "Admin role required": "Dafür brauchst du Admin-Rechte.",
  "Number already in use": "Diese Nr ist schon vergeben.",
  "Name already in use": "Dieser Name ist schon vergeben.",
  "E-mail already in use": "Diese E-Mail ist schon vergeben.",
  "Current password is wrong": "Das aktuelle Passwort stimmt nicht.",
  "Invalid code": "Der Code stimmt nicht. Prüfe die Uhrzeit auf dem Handy.",
  "Invalid password or code": "Passwort oder Code stimmen nicht.",
  "Invalid or expired token": "Der Link ist abgelaufen oder wurde schon benutzt.",
  "This certification requires an expiry date": "Für diesen Nachweis muss ein Ablaufdatum angegeben werden.",
  "Date lies in the future": "Das Datum liegt in der Zukunft.",
  "The last active admin cannot be removed": "Der letzte aktive Admin kann nicht entfernt werden.",
  "Certification has completions – deactivate it instead":
    "Für diesen Nachweis gibt es Einträge. Deaktiviere ihn stattdessen.",
  "Only the recording user or an admin may delete": "Nur wer den Eintrag angelegt hat oder ein Admin darf ihn löschen.",
  "User is deactivated": "Der Benutzer ist gesperrt. Entsperre ihn zuerst.",
  "2FA already enabled": "Zwei-Faktor ist bereits eingeschaltet.",
  "2FA not enabled": "Zwei-Faktor ist nicht eingeschaltet.",
  "Run setup first": "Richte Zwei-Faktor zuerst ein.",
  "Certification not found": GONE,
  "Completion not found": GONE,
  "Member not found": GONE,
  "Position not found": GONE,
  "User not found": GONE,
  "Unknown certification id": STALE,
  "Unknown member id": STALE,
  "Unknown position id": STALE,
};

/** Maps backend error messages (English) to user-facing German text. */
export function errorText(e: unknown): string {
  if (!(e instanceof ApiError)) return "Keine Verbindung zum Server.";
  return ERROR_TEXT[e.message] ?? e.message;
}
