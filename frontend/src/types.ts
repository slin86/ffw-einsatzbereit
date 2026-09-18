export type Role = "admin" | "user";
export type CellStatus = "missing" | "expired" | "expiring" | "valid" | "not_required";
export type CertificationKind = "seminar" | "exercise" | "test" | "training";
export type ValidityMode = "unlimited" | "fixed_duration" | "end_of_year" | "manual";

export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  totp_enabled: boolean;
}

export interface Certification {
  id: number;
  name: string;
  short_name: string;
  kind: CertificationKind;
  description: string;
  validity_mode: ValidityMode;
  validity_months: number | null;
  warn_days: number;
  sort_order: number;
  is_active: boolean;
}

export interface Ref {
  id: number;
  name: string;
}

export interface Position {
  id: number;
  name: string;
  description: string;
  certifications: Ref[];
}

export interface Member {
  id: number;
  number: string;
  last_name: string;
  first_name: string;
  is_active: boolean;
  positions: Ref[];
}

export interface Cell {
  certification_id: number;
  required: boolean;
  status: CellStatus;
  completed_on: string | null;
  expires_on: string | null;
}

export interface MatrixRow {
  member: Member;
  worst_status: CellStatus;
  open_count: number;
  cells: Cell[];
}

export interface Overview {
  today: string;
  certifications: Certification[];
  rows: MatrixRow[];
  counts: Record<CellStatus, number>;
}

export interface Completion {
  id: number;
  member_id: number;
  certification_id: number;
  certification_name: string;
  completed_on: string;
  expires_on: string | null;
  note: string;
  recorded_by: string | null;
  recorded_by_id: number | null;
  recorded_at: string;
}

export interface MemberDetail {
  member: Member;
  cells: Cell[];
  history: Completion[];
}

export interface TokenResponse {
  access_token: string | null;
  mfa_required: boolean;
  mfa_token: string | null;
}
