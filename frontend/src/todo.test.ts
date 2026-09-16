import { describe, expect, it } from "vitest";

import { buildOpenRows } from "./todo";
import type { Cell, CellStatus, MatrixRow } from "./types";

function cell(id: number, status: CellStatus): Cell {
  return { certification_id: id, required: status !== "not_required", status, completed_on: null, expires_on: null };
}

function row(id: number, last: string, first: string, statuses: CellStatus[], worst: CellStatus): MatrixRow {
  return {
    member: { id, number: String(id), last_name: last, first_name: first, is_active: true, positions: [] },
    worst_status: worst,
    open_count: statuses.filter((s) => ["missing", "expired", "expiring"].includes(s)).length,
    cells: statuses.map((s, i) => cell(i + 1, s)),
  };
}

describe("buildOpenRows", () => {
  const rows = [
    row(1, "Albers", "Anna", ["valid", "valid"], "valid"),
    row(2, "Brandt", "Ben", ["expiring", "valid"], "expiring"),
    row(3, "Claußen", "Clara", ["valid", "expired"], "expired"),
    row(4, "Dreyer", "Dirk", ["expiring", "missing", "expired"], "missing"),
    row(5, "Ehlers", "Eva", ["missing", "not_required"], "missing"),
    row(6, "Özdemir", "Ali", ["expiring", "expiring"], "expiring"),
    row(7, "Brandt", "Anja", ["expiring", "valid"], "expiring"),
  ];

  it("drops members without open items", () => {
    expect(buildOpenRows(rows).map((r) => r.member.id)).not.toContain(1);
  });

  it("sorts by worst status, then open count, then name", () => {
    expect(buildOpenRows(rows).map((r) => r.member.id)).toEqual([4, 5, 3, 6, 7, 2]);
  });

  it("lists open cells by severity and excludes the rest", () => {
    const dreyer = buildOpenRows(rows)[0]!;
    expect(dreyer.open.map((c) => c.status)).toEqual(["missing", "expired", "expiring"]);
    const ehlers = buildOpenRows(rows)[1]!;
    expect(ehlers.open.map((c) => c.status)).toEqual(["missing"]);
  });

  it("does not mutate its input", () => {
    const copy = structuredClone(rows);
    buildOpenRows(rows);
    expect(rows).toEqual(copy);
  });

  it("handles an empty list", () => {
    expect(buildOpenRows([])).toEqual([]);
  });
});
