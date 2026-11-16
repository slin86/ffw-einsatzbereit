import { describe, expect, it } from "vitest";

import { buildOpenRows } from "../todo";
import type { Cell, CellStatus, Certification, MatrixRow, Member } from "../types";
import {
  certStats,
  dueText,
  groupByLetter,
  groupByStatus,
  indexLetter,
  initials,
  memberState,
  openCount,
  parseIds,
  readiness,
  readRecent,
  RECENT_KEY,
  rememberRecent,
  segmentCounts,
  segmentRows,
  splitRecent,
  validityText,
} from "./readiness";

function member(id: number, last: string, first = "Max"): Member {
  return { id, number: String(id), last_name: last, first_name: first, is_active: true, positions: [] };
}

function cell(certification_id: number, status: CellStatus, expires_on: string | null = null, required = true): Cell {
  return { certification_id, required, status, completed_on: null, expires_on };
}

function row(m: Member, cells: Cell[], worst: CellStatus): MatrixRow {
  return { member: m, cells, worst_status: worst, open_count: 0 };
}

function cert(id: number, name: string): Certification {
  return {
    id,
    name,
    short_name: "",
    kind: "test",
    description: "",
    validity_mode: "unlimited",
    validity_months: null,
    warn_days: 30,
    sort_order: id,
    is_active: true,
  };
}

const rows: MatrixRow[] = [
  row(member(1, "Arndt"), [cell(1, "missing"), cell(2, "valid")], "missing"),
  row(member(2, "Böhm"), [cell(1, "expiring", "2026-11-20"), cell(2, "valid")], "expiring"),
  row(member(3, "Claus"), [cell(1, "valid"), cell(2, "expired", "2026-10-01")], "expired"),
  row(member(4, "Dorn"), [cell(1, "valid"), cell(2, "not_required", null, false)], "valid"),
  row(member(5, "Ebert"), [cell(1, "expiring", "2026-11-17"), cell(2, "missing")], "missing"),
];

describe("member readiness", () => {
  it("classifies members", () => {
    expect(memberState({ worst_status: "missing" })).toBe("critical");
    expect(memberState({ worst_status: "expired" })).toBe("critical");
    expect(memberState({ worst_status: "expiring" })).toBe("soon");
    expect(memberState({ worst_status: "valid" })).toBe("ready");
    expect(memberState({ worst_status: "not_required" })).toBe("ready");
  });

  it("counts ready members, expiring ones included", () => {
    expect(readiness(rows)).toEqual({ total: 5, ready: 2, soon: 1, critical: 3 });
    expect(readiness([])).toEqual({ total: 0, ready: 0, soon: 0, critical: 0 });
  });

  it("splits open rows into segments", () => {
    const open = buildOpenRows(rows);
    expect(segmentRows(open, "all")).toHaveLength(4);
    const critical = segmentRows(open, "critical");
    expect(critical.map((r) => r.member.id)).toEqual([5, 1, 3]);
    expect(critical.find((r) => r.member.id === 5)!.open.map((c) => c.status)).toEqual(["missing"]);
    expect(segmentRows(open, "soon").map((r) => r.member.id)).toEqual([5, 2]);
    expect(segmentCounts(open)).toEqual({ all: 4, critical: 3, soon: 2 });
  });

  it("counts open cells", () => {
    expect(openCount(rows[4]!)).toBe(2);
    expect(openCount(rows[3]!)).toBe(0);
  });
});

describe("certification stats", () => {
  it("aggregates required cells and sorts by urgency", () => {
    const stats = certStats({ certifications: [cert(1, "A"), cert(2, "B"), cert(3, "C")], rows });
    expect(stats.map((s) => s.certification.id)).toEqual([2, 1, 3]);
    expect(stats[1]).toMatchObject({ required: 5, missing: 1, expiring: 2, valid: 2, expired: 0 });
    expect(stats[0]).toMatchObject({ required: 4, missing: 1, expired: 1, valid: 2 });
    expect(stats[2]!.required).toBe(0);
  });

  it("puts certifications with more critical items first", () => {
    const r = [row(member(1, "A"), [cell(2, "expired"), cell(1, "expiring")], "expired")];
    const stats = certStats({ certifications: [cert(1, "A"), cert(2, "B")], rows: r });
    expect(stats.map((s) => s.certification.id)).toEqual([2, 1]);
  });

  it("ignores cells of unknown certifications", () => {
    const r = [row(member(1, "A"), [cell(9, "missing")], "missing")];
    expect(certStats({ certifications: [cert(1, "A")], rows: r })[0]!.required).toBe(0);
  });

  it("groups members by status for one certification", () => {
    const groups = groupByStatus({ rows }, 1);
    expect(groups.map((g) => g.status)).toEqual(["missing", "expiring", "valid"]);
    expect(groups[1]!.entries.map((e) => e.member.id)).toEqual([5, 2]);
    expect(groups[2]!.entries.map((e) => e.member.last_name)).toEqual(["Claus", "Dorn"]);
    expect(groupByStatus({ rows }, 2).map((g) => g.status)).toEqual(["missing", "expired", "valid", "not_required"]);
    expect(groupByStatus({ rows }, 7)).toEqual([]);
  });

  it("orders expiring entries without date and equal dates by name", () => {
    const r = [
      row(member(1, "Zander"), [cell(1, "expiring", "2026-12-01")], "expiring"),
      row(member(2, "Abel"), [cell(1, "expiring", "2026-12-01")], "expiring"),
      row(member(3, "Mai"), [cell(1, "expiring", null)], "expiring"),
    ];
    expect(groupByStatus({ rows: r }, 1)[0]!.entries.map((e) => e.member.id)).toEqual([3, 2, 1]);
  });
});

describe("names", () => {
  it("builds index letters", () => {
    expect(indexLetter("Özdemir")).toBe("O");
    expect(indexLetter(" müller")).toBe("M");
    expect(indexLetter("1. Zug")).toBe("#");
    expect(indexLetter("")).toBe("#");
  });

  it("groups by letter in German order", () => {
    const items = [member(1, "Ohm"), member(2, "Öztürk"), member(3, "Adam"), member(4, "Adam", "Anna")].map((m) => ({
      member: m,
    }));
    const groups = groupByLetter(items);
    expect(groups.map((g) => g.letter)).toEqual(["A", "O"]);
    expect(groups[0]!.items.map((i) => i.member.id)).toEqual([4, 3]);
    expect(groups[1]!.items.map((i) => i.member.id)).toEqual([1, 2]);
  });

  it("builds initials", () => {
    expect(initials({ first_name: "jana", last_name: "Wolf" })).toBe("JW");
    expect(initials({ first_name: "", last_name: "" })).toBe("?");
  });
});

describe("due text", () => {
  const today = "2026-11-16";
  it("describes every status", () => {
    expect(dueText({ status: "missing", expires_on: null, completed_on: null }, today)).toBe("Fehlt");
    expect(dueText({ status: "expired", expires_on: null, completed_on: null }, today)).toBe("Abgelaufen");
    expect(dueText({ status: "expired", expires_on: "2026-11-15", completed_on: null }, today)).toBe(
      "Abgelaufen seit 1 Tag",
    );
    expect(dueText({ status: "expired", expires_on: "2026-11-06", completed_on: null }, today)).toBe(
      "Abgelaufen seit 10 Tagen",
    );
    expect(dueText({ status: "expired", expires_on: "2026-09-16", completed_on: null }, today)).toBe(
      "Abgelaufen seit 2 Monaten",
    );
    expect(dueText({ status: "expired", expires_on: "2026-09-30", completed_on: null }, today)).toBe(
      "Abgelaufen seit 2 Monaten",
    );
    expect(dueText({ status: "expired", expires_on: "2025-10-16", completed_on: null }, today)).toBe(
      "Abgelaufen seit 13 Monaten",
    );
    expect(dueText({ status: "expired", expires_on: "2025-11-16", completed_on: null }, today)).toBe(
      "Abgelaufen seit 12 Monaten",
    );
    expect(dueText({ status: "expired", expires_on: "2025-01-01", completed_on: null }, today)).toBe(
      "Abgelaufen seit 2 Jahren",
    );
    expect(dueText({ status: "expired", expires_on: "2025-05-25", completed_on: null }, today)).toBe(
      "Abgelaufen seit 1 Jahr",
    );
    expect(dueText({ status: "expired", expires_on: "2026-10-02", completed_on: null }, today)).toBe(
      "Abgelaufen seit 1 Monat",
    );
    expect(dueText({ status: "expiring", expires_on: "2026-11-16", completed_on: null }, today)).toBe("Läuft heute ab");
    expect(dueText({ status: "expiring", expires_on: null, completed_on: null }, today)).toBe("Läuft heute ab");
    expect(dueText({ status: "expiring", expires_on: "2026-11-17", completed_on: null }, today)).toBe(
      "Läuft morgen ab",
    );
    expect(dueText({ status: "expiring", expires_on: "2026-11-30", completed_on: null }, today)).toBe(
      "Läuft in 14 Tagen ab",
    );
    expect(dueText({ status: "valid", expires_on: "2027-03-12", completed_on: null }, today)).toBe(
      "Gültig bis 12.03.2027",
    );
    expect(dueText({ status: "valid", expires_on: null, completed_on: null }, today)).toBe("Unbefristet gültig");
    expect(dueText({ status: "not_required", expires_on: null, completed_on: "2025-02-03" }, today)).toBe(
      "Zuletzt 03.02.2025",
    );
    expect(dueText({ status: "not_required", expires_on: null, completed_on: null }, today)).toBe("Nicht gefordert");
  });
});

describe("recent certifications", () => {
  function memory(initial?: string) {
    const data = new Map<string, string>(initial === undefined ? [] : [[RECENT_KEY, initial]]);
    return {
      data,
      getItem: (k: string) => data.get(k) ?? null,
      setItem: (k: string, v: string) => void data.set(k, v),
    };
  }
  const broken = {
    getItem: () => {
      throw new Error("x");
    },
    setItem: () => {
      throw new Error("x");
    },
  };

  it("reads only valid ids", () => {
    expect(readRecent(memory('[3, 1.5, "x", 2]'))).toEqual([3, 2]);
    expect(readRecent(memory("{}"))).toEqual([]);
    expect(readRecent(memory("nope"))).toEqual([]);
    expect(readRecent(memory())).toEqual([]);
    expect(readRecent(null)).toEqual([]);
    expect(readRecent(broken)).toEqual([]);
  });

  it("moves an id to the front and keeps four", () => {
    const s = memory("[1,2,3,4]");
    expect(rememberRecent(3, s)).toEqual([3, 1, 2, 4]);
    expect(rememberRecent(9, s)).toEqual([9, 3, 1, 2]);
    expect(JSON.parse(s.data.get(RECENT_KEY)!)).toEqual([9, 3, 1, 2]);
    expect(rememberRecent(5, broken)).toEqual([5]);
  });

  it("splits a list into recent and rest", () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(splitRecent(items, [3, 8, 1])).toEqual({ recent: [{ id: 3 }, { id: 1 }], rest: [{ id: 2 }] });
  });
});

describe("parseIds", () => {
  it("parses comma separated ids", () => {
    expect(parseIds("3,1,x,3,,7")).toEqual([3, 1, 7]);
    expect(parseIds(["5,6", "7"])).toEqual([5, 6]);
    expect(parseIds(undefined)).toEqual([]);
    expect(parseIds(null)).toEqual([]);
  });
});

describe("validityText", () => {
  it("describes each rule", () => {
    expect(validityText({ validity_mode: "unlimited", validity_months: null })).toBe("unbefristet");
    expect(validityText({ validity_mode: "fixed_duration", validity_months: 12 })).toBe("gilt 12 Monate ab Abschluss");
    expect(validityText({ validity_mode: "fixed_duration", validity_months: 1 })).toBe("gilt 1 Monat ab Abschluss");
    expect(validityText({ validity_mode: "fixed_duration", validity_months: null })).toBe("unbefristet");
    expect(validityText({ validity_mode: "end_of_year", validity_months: 24 })).toBe(
      "gilt 24 Monate, dann bis Jahresende",
    );
    expect(validityText({ validity_mode: "end_of_year", validity_months: null })).toBe("unbefristet");
    expect(validityText({ validity_mode: "manual", validity_months: null })).toBe("Ablaufdatum je Eintrag");
  });
});
