import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  api,
  ApiError,
  download,
  ERROR_TEXT,
  errorText,
  refreshAccessToken,
  setAccessToken,
  setAuthLostHandler,
} from "./api";

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

let calls: { url: string; init: RequestInit }[] = [];

function mockFetch(handler: Handler): void {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return handler(url, init);
    }),
  );
}

function authHeader(i: number): string | null {
  return new Headers(calls[i]!.init.headers).get("Authorization");
}

beforeEach(() => {
  setAccessToken(null);
  setAuthLostHandler(() => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("api", () => {
  it("sends JSON with the bearer token and same-origin credentials", async () => {
    setAccessToken("tok");
    mockFetch(() => json(200, { ok: true }));
    await expect(api("/api/members", "POST", { a: 1 })).resolves.toEqual({ ok: true });
    const { init } = calls[0]!;
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"a":1}');
    expect(init.credentials).toBe("same-origin");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(authHeader(0)).toBe("Bearer tok");
  });

  it("omits body, content type and token when not needed", async () => {
    mockFetch(() => json(200, []));
    await api("/api/members");
    const headers = new Headers(calls[0]!.init.headers);
    expect(calls[0]!.init.body).toBeUndefined();
    expect(headers.has("Content-Type")).toBe(false);
    expect(headers.has("Authorization")).toBe(false);
  });

  it.each([202, 204])("returns undefined for status %i", async (status) => {
    mockFetch(() => new Response(null, { status }));
    await expect(api("/api/x", "POST")).resolves.toBeUndefined();
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    setAccessToken("old");
    mockFetch((url, init) => {
      if (url === "/api/auth/refresh") return json(200, { access_token: "new", mfa_required: false });
      const auth = new Headers(init.headers).get("Authorization");
      return auth === "Bearer new" ? json(200, { id: 1 }) : json(401, { detail: "Not authenticated" });
    });
    await expect(api("/api/me")).resolves.toEqual({ id: 1 });
    expect(calls.map((c) => c.url)).toEqual(["/api/me", "/api/auth/refresh", "/api/me"]);
    expect(authHeader(2)).toBe("Bearer new");
  });

  it("signals lost authentication when refresh fails", async () => {
    setAccessToken("old");
    const lost = vi.fn();
    setAuthLostHandler(lost);
    mockFetch((url) => (url === "/api/auth/refresh" ? json(401, {}) : json(401, { detail: "Not authenticated" })));
    await expect(api("/api/me")).rejects.toMatchObject({ status: 401, message: "Not authenticated" });
    expect(lost).toHaveBeenCalledOnce();
    mockFetch(() => json(200, {}));
    await api("/api/me");
    expect(authHeader(0)).toBeNull();
  });

  it("does not retry auth endpoints", async () => {
    mockFetch(() => json(401, { detail: "Invalid credentials" }));
    await expect(api("/api/auth/login", "POST", {})).rejects.toBeInstanceOf(ApiError);
    expect(calls).toHaveLength(1);
  });

  it("does not retry twice", async () => {
    mockFetch((url) =>
      url === "/api/auth/refresh" ? json(200, { access_token: "t" }) : json(401, { detail: "Not authenticated" }),
    );
    await expect(api("/api/me")).rejects.toMatchObject({ status: 401 });
    expect(calls.map((c) => c.url)).toEqual(["/api/me", "/api/auth/refresh", "/api/me"]);
  });

  it.each([
    [json(409, { detail: "Name already in use" }), "Name already in use"],
    [json(422, { detail: [{ loc: ["body", "name"] }] }), "Eingaben unvollständig oder ungültig"],
    [new Response("<html>oops</html>", { status: 502, statusText: "Bad Gateway" }), "Bad Gateway"],
    [json(500, { detail: 42 }, {}), ""],
  ])("turns error responses into ApiError (%#)", async (response, message) => {
    mockFetch(() => response);
    const err = await api("/api/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(response.status);
    expect((err as ApiError).message).toBe(message);
  });
});

describe("refreshAccessToken", () => {
  it("shares one request between concurrent callers", async () => {
    let resolve!: (r: Response) => void;
    mockFetch(() => new Promise<Response>((r) => (resolve = r)));
    const a = refreshAccessToken();
    const b = refreshAccessToken();
    expect(calls).toHaveLength(1);
    resolve(json(200, { access_token: "x" }));
    await expect(Promise.all([a, b])).resolves.toEqual([true, true]);
    mockFetch(() => json(200, { access_token: "y" }));
    await refreshAccessToken();
    expect(calls).toHaveLength(1);
  });

  it("returns false on network errors and missing tokens", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(refreshAccessToken()).resolves.toBe(false);
    mockFetch(() => json(200, { access_token: null, mfa_required: false }));
    await expect(refreshAccessToken()).resolves.toBe(false);
  });
});

describe("download", () => {
  function stubDom() {
    const anchor = { href: "", download: "", click: vi.fn() };
    vi.stubGlobal("document", { createElement: vi.fn(() => anchor) });
    const createObjectURL = vi.fn(() => "blob:1");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    return { anchor, revokeObjectURL };
  }

  it("saves the file under the server-provided name", async () => {
    vi.useFakeTimers();
    const { anchor, revokeObjectURL } = stubDom();
    mockFetch(
      () =>
        new Response("a;b", {
          status: 200,
          headers: { "Content-Disposition": 'attachment; filename="einsatzbereit-2026-09-16.csv"' },
        }),
    );
    await download("/api/exports/csv?only_open=true");
    expect(calls[0]!.url).toBe("/api/exports/csv?only_open=true");
    expect(anchor).toMatchObject({ href: "blob:1", download: "einsatzbereit-2026-09-16.csv" });
    expect(anchor.click).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(1000);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:1");
  });

  it("falls back to a generic name", async () => {
    const { anchor } = stubDom();
    mockFetch(() => new Response("x", { status: 200 }));
    await download("/api/exports/pdf");
    expect(anchor.download).toBe("export");
  });
});

describe("errorText", () => {
  it("translates known messages and passes through unknown ones", () => {
    expect(errorText(new ApiError(401, "Invalid credentials"))).toBe(ERROR_TEXT["Invalid credentials"]);
    expect(errorText(new ApiError(404, "Member not found"))).toContain("Nicht mehr vorhanden");
    expect(errorText(new ApiError(418, "Teapot"))).toBe("Teapot");
  });

  it("reports connection problems for non-API errors", () => {
    expect(errorText(new TypeError("Failed to fetch"))).toBe("Keine Verbindung zum Server.");
  });

  it("has a German text for every entry", () => {
    for (const text of Object.values(ERROR_TEXT)) expect(text).toMatch(/[.]$/);
  });
});

describe("without an auth-lost handler", () => {
  it("still rejects cleanly", async () => {
    vi.resetModules();
    const fresh = await import("./api");
    mockFetch(() => json(401, { detail: "Not authenticated" }));
    await expect(fresh.api("/api/me")).rejects.toMatchObject({ status: 401 });
  });
});
