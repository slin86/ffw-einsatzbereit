import { describe, expect, it } from "vitest";

import { actionText, changeLines, formatValue } from "./auditText";

describe("actionText", () => {
  it("names the action per entity", () => {
    expect(actionText({ entity_type: "completion", action: "create" })).toBe("Abschluss eingetragen");
    expect(actionText({ entity_type: "member", action: "update" })).toBe("Kamerad geändert");
    expect(actionText({ entity_type: "position", action: "delete" })).toBe("Funktion gelöscht");
  });
});

describe("formatValue", () => {
  it("formats booleans, lists, dates, enums and empties", () => {
    expect(formatValue("is_active", false)).toBe("nein");
    expect(formatValue("positions", ["AGT", "Maschinist"])).toBe("AGT, Maschinist");
    expect(formatValue("positions", [])).toBe("keine");
    expect(formatValue("completed_on", "2026-03-10")).toBe("10.03.2026");
    expect(formatValue("kind", "exercise")).toBe("Übung");
    expect(formatValue("validity_mode", "end_of_year")).toBe("Bis Jahresende nach Dauer");
    expect(formatValue("role", "admin")).toBe("Admin");
    expect(formatValue("note", "")).toBe("–");
    expect(formatValue("warn_days", 30)).toBe("30");
  });
  it("keeps unknown enum values readable", () => {
    expect(formatValue("kind", "drill")).toBe("drill");
  });
});

describe("changeLines", () => {
  it("shows old and new values for updates", () => {
    expect(
      changeLines({
        action: "update",
        changes: { first_name: ["Ida", "Ina"], is_active: [true, false], positions: [["Basis"], []] },
      }).map((l) => l.text),
    ).toEqual(["Vorname: Ida → Ina", "Aktiv: ja → nein", "Funktionen: Basis → keine"]);
  });

  it("lists non-empty values for creates and deletes", () => {
    expect(
      changeLines({
        action: "delete",
        changes: { certification: "Erste Hilfe", completed_on: "2026-01-10", manual_expires_on: null, note: "" },
      }).map((l) => l.text),
    ).toEqual(["Nachweis: Erste Hilfe", "Abgeschlossen am: 10.01.2026"]);
  });

  it("falls back to the raw field name", () => {
    expect(changeLines({ action: "create", changes: { foo: 1 } })[0]!.text).toBe("foo: 1");
  });
});
