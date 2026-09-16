import { formatDate, KIND_LABEL, VALIDITY_LABEL } from "./labels";
import type { CertificationKind, ValidityMode } from "./types";

export type AuditEntityType = "member" | "completion" | "certification" | "position" | "user";
export type AuditAction = "create" | "update" | "delete";

export interface AuditEntry {
  id: number;
  at: string;
  user_name: string;
  entity_type: AuditEntityType;
  entity_id: number;
  entity_label: string;
  member_id: number | null;
  action: AuditAction;
  changes: Record<string, unknown>;
}

export interface AuditPage {
  entries: AuditEntry[];
  next_before_id: number | null;
}

export const ENTITY_LABEL: Record<AuditEntityType, string> = {
  member: "Kamerad",
  completion: "Abschluss",
  certification: "Nachweis",
  position: "Funktion",
  user: "Benutzer",
};

const ACTION_VERB: Record<AuditEntityType, Record<AuditAction, string>> = {
  member: { create: "Kamerad angelegt", update: "Kamerad geändert", delete: "Kamerad gelöscht" },
  completion: { create: "Abschluss eingetragen", update: "Abschluss geändert", delete: "Abschluss gelöscht" },
  certification: { create: "Nachweis angelegt", update: "Nachweis geändert", delete: "Nachweis gelöscht" },
  position: { create: "Funktion angelegt", update: "Funktion geändert", delete: "Funktion gelöscht" },
  user: { create: "Benutzer angelegt", update: "Benutzer geändert", delete: "Benutzer gelöscht" },
};

const FIELD_LABEL: Record<string, string> = {
  number: "Nr",
  last_name: "Name",
  first_name: "Vorname",
  is_active: "Aktiv",
  positions: "Funktionen",
  certification: "Nachweis",
  completed_on: "Abgeschlossen am",
  manual_expires_on: "Gültig bis",
  note: "Bemerkung",
  name: "Name",
  short_name: "Kürzel",
  kind: "Art",
  description: "Beschreibung",
  validity_mode: "Gültigkeit",
  validity_months: "Dauer (Monate)",
  warn_days: "Warnen ab (Tage)",
  sort_order: "Reihenfolge",
  certifications: "Geforderte Nachweise",
  email: "E-Mail",
  display_name: "Anzeigename",
  role: "Rolle",
  totp_enabled: "Zwei-Faktor",
};

const ROLE_LABEL: Record<string, string> = { admin: "Admin", user: "Anwender" };

export function actionText(e: Pick<AuditEntry, "entity_type" | "action">): string {
  return ACTION_VERB[e.entity_type]?.[e.action] ?? `${e.entity_type} ${e.action}`;
}

export function fieldLabel(field: string): string {
  return FIELD_LABEL[field] ?? field;
}

export function formatValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "–";
  if (typeof value === "boolean") return value ? "ja" : "nein";
  if (Array.isArray(value)) return value.length ? value.map(String).join(", ") : "keine";
  if (typeof value === "string") {
    if (field === "kind") return KIND_LABEL[value as CertificationKind] ?? value;
    if (field === "validity_mode") return VALIDITY_LABEL[value as ValidityMode] ?? value;
    if (field === "role") return ROLE_LABEL[value] ?? value;
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return formatDate(value);
  }
  return String(value);
}

export interface ChangeLine {
  field: string;
  text: string;
}

/**
 * Human-readable change lines. Updates show "old → new"; creates and deletes list the
 * non-empty values (so the log still says what was deleted).
 */
export function changeLines(e: Pick<AuditEntry, "action" | "changes">): ChangeLine[] {
  return Object.entries(e.changes)
    .filter(([, v]) => e.action === "update" || !(v === null || v === "" || (Array.isArray(v) && !v.length)))
    .map(([field, v]) => {
      const label = fieldLabel(field);
      if (e.action === "update" && Array.isArray(v) && v.length === 2) {
        return { field, text: `${label}: ${formatValue(field, v[0])} → ${formatValue(field, v[1])}` };
      }
      return { field, text: `${label}: ${formatValue(field, v)}` };
    });
}
