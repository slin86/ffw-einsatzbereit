import { describe, expect, it } from "vitest";

import { cellHint, daysUntil, formatDate, formatDateTime, shortName } from "./labels";

describe("formatDate", () => {
  it("formats ISO dates in German order", () => {
    expect(formatDate("2026-03-09")).toBe("09.03.2026");
  });
  it("uses the date part of timestamps", () => {
    expect(formatDate("2026-12-31T23:30:00+00:00")).toBe("31.12.2026");
  });
  it("shows a dash for missing values", () => {
    expect(formatDate(null)).toBe("–");
    expect(formatDate("")).toBe("–");
  });
});

describe("formatDateTime", () => {
  it("converts UTC to German time in winter and summer", () => {
    expect(formatDateTime("2026-01-15T11:05:00Z")).toBe("15.01.2026, 12:05");
    expect(formatDateTime("2026-07-15T11:05:00+00:00")).toBe("15.07.2026, 13:05");
  });
  it("moves late UTC times to the next day", () => {
    expect(formatDateTime("2026-12-31T23:30:00Z")).toBe("01.01.2027, 00:30");
  });
  it("handles garbage", () => {
    expect(formatDateTime("nope")).toBe("–");
  });
});

describe("daysUntil", () => {
  it("counts calendar days", () => {
    expect(daysUntil("2026-09-20", "2026-09-16")).toBe(4);
    expect(daysUntil("2026-09-16", "2026-09-16")).toBe(0);
    expect(daysUntil("2026-09-10", "2026-09-16")).toBe(-6);
  });
  it("is not affected by daylight saving changes", () => {
    // DST ends 2026-10-25, starts 2027-03-28 in Germany
    expect(daysUntil("2026-10-26", "2026-10-24")).toBe(2);
    expect(daysUntil("2027-03-29", "2027-03-27")).toBe(2);
  });
  it("handles leap years and year boundaries", () => {
    expect(daysUntil("2028-03-01", "2028-02-28")).toBe(2);
    expect(daysUntil("2027-01-01", "2026-12-31")).toBe(1);
  });
  it("returns null without a date", () => {
    expect(daysUntil(null, "2026-09-16")).toBeNull();
  });
});

describe("cellHint", () => {
  const today = "2026-09-16";
  it("describes each status", () => {
    expect(cellHint("missing", null, today)).toBe("fehlt");
    expect(cellHint("valid", "2027-03-09", today)).toBe("bis 09.03.2027");
    expect(cellHint("valid", null, today)).toBe("unbefristet");
    expect(cellHint("expired", "2026-09-15", today)).toBe("seit 15.09.2026");
    expect(cellHint("expiring", "2026-09-30", today)).toBe("noch 14 T.");
    expect(cellHint("expiring", today, today)).toBe("heute");
    expect(cellHint("not_required", null, today)).toBe("");
    expect(cellHint("not_required", "2025-01-01", today)).toBe("01.01.2025");
  });
});

describe("shortName", () => {
  it("prefers the configured abbreviation", () => {
    expect(shortName("Belastungsübung Atemschutz", "AGT-Ü")).toBe("AGT-Ü");
  });
  it("builds initials for multi-word names", () => {
    expect(shortName("Belastungsübung Atemschutz", "")).toBe("BA");
    expect(shortName("Erste-Hilfe Kurs für Einsatzkräfte", "")).toBe("EHKF");
  });
  it("truncates single words", () => {
    expect(shortName("Sprechfunk", "")).toBe("Spre");
  });
});
