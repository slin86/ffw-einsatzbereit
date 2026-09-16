import { describe, expect, it } from "vitest";

import { accessGuard, safeNext } from "./guard";
import type { User } from "./types";

const base: User = { id: 1, email: "a@b.de", display_name: "A", role: "user", is_active: true, totp_enabled: false };
const admin: User = { ...base, role: "admin" };

const route = (fullPath: string, meta: Record<string, boolean> = {}) => ({ fullPath, meta });

describe("accessGuard", () => {
  it("lets everyone reach public pages", () => {
    expect(accessGuard(route("/login", { public: true }), null)).toBe(true);
  });

  it("sends anonymous users to the login with a return path", () => {
    expect(accessGuard(route("/uebersicht?only_open=true"), null)).toEqual({
      path: "/login",
      query: { next: "/uebersicht?only_open=true" },
    });
  });

  it("keeps non-admins out of the admin area", () => {
    expect(accessGuard(route("/admin/benutzer", { admin: true }), base)).toBe("/");
    expect(accessGuard(route("/admin/benutzer", { admin: true }), admin)).toBe(true);
  });

  it("lets logged-in users through", () => {
    expect(accessGuard(route("/kameraden"), base)).toBe(true);
  });
});

describe("safeNext", () => {
  it.each([
    ["/uebersicht?q=a", "/uebersicht?q=a"],
    ["//evil.example/x", "/"],
    ["https://evil.example", "/"],
    ["uebersicht", "/"],
    [undefined, "/"],
    [["/a"], "/"],
  ])("safeNext(%j) = %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});
