import type { Cell, CellStatus, MatrixRow } from "./types";

export const SEVERITY: Record<CellStatus, number> = {
  missing: 0,
  expired: 1,
  expiring: 2,
  valid: 3,
  not_required: 4,
};

const OPEN: ReadonlySet<CellStatus> = new Set(["missing", "expired", "expiring"]);

export function isOpen(status: CellStatus): boolean {
  return OPEN.has(status);
}

export interface OpenRow extends MatrixRow {
  open: Cell[];
}

/**
 * Returns the members with open items, most urgent first. Rows are ordered by worst status, then by number of open
 * items, then by name. Open items inside a row are ordered by severity.
 */
export function buildOpenRows(rows: MatrixRow[]): OpenRow[] {
  return rows
    .filter((r) => r.cells.some((c) => isOpen(c.status)))
    .map((r) => ({
      ...r,
      open: r.cells.filter((c) => isOpen(c.status)).sort((a, b) => SEVERITY[a.status] - SEVERITY[b.status]),
    }))
    .sort(
      (a, b) =>
        SEVERITY[a.worst_status] - SEVERITY[b.worst_status] ||
        b.open.length - a.open.length ||
        a.member.last_name.localeCompare(b.member.last_name, "de") ||
        a.member.first_name.localeCompare(b.member.first_name, "de"),
    );
}
