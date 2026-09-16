import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  api: vi.fn(),
  refreshAccessToken: vi.fn(),
  setAccessToken: vi.fn(),
}));
vi.mock("./api", () => apiMock);

import { login, loginMfa, logout, restoreSession, session } from "./session";
import type { User } from "./types";

const user: User = {
  id: 1,
  email: "a@example.org",
  display_name: "Anna",
  role: "user",
  is_active: true,
  totp_enabled: false,
};

beforeEach(() => {
  vi.resetAllMocks();
  session.user = null;
  session.ready = false;
});

describe("restoreSession", () => {
  it("loads the user when the refresh cookie is valid", async () => {
    apiMock.refreshAccessToken.mockResolvedValue(true);
    apiMock.api.mockResolvedValue(user);
    await restoreSession();
    expect(session).toMatchObject({ user, ready: true });
    expect(apiMock.api).toHaveBeenCalledWith("/api/me");
  });

  it("stays logged out without a valid cookie", async () => {
    apiMock.refreshAccessToken.mockResolvedValue(false);
    await restoreSession();
    expect(session).toMatchObject({ user: null, ready: true });
    expect(apiMock.api).not.toHaveBeenCalled();
  });

  it("stays logged out when loading the user fails", async () => {
    apiMock.refreshAccessToken.mockResolvedValue(true);
    apiMock.api.mockRejectedValue(new Error("boom"));
    await restoreSession();
    expect(session).toMatchObject({ user: null, ready: true });
  });
});

describe("login", () => {
  it("stores the token and loads the user", async () => {
    apiMock.api.mockResolvedValueOnce({ access_token: "t", mfa_required: false, mfa_token: null });
    apiMock.api.mockResolvedValueOnce(user);
    await expect(login("a@example.org", "pw")).resolves.toBeNull();
    expect(apiMock.api).toHaveBeenNthCalledWith(1, "/api/auth/login", "POST", {
      email: "a@example.org",
      password: "pw",
    });
    expect(apiMock.setAccessToken).toHaveBeenCalledWith("t");
    expect(session.user).toEqual(user);
  });

  it("returns the MFA token when a second factor is required", async () => {
    apiMock.api.mockResolvedValueOnce({ access_token: null, mfa_required: true, mfa_token: "m" });
    await expect(login("a@example.org", "pw")).resolves.toBe("m");
    expect(apiMock.setAccessToken).not.toHaveBeenCalled();
    expect(session.user).toBeNull();
  });

  it("completes the MFA step", async () => {
    apiMock.api.mockResolvedValueOnce({ access_token: "t2", mfa_required: false, mfa_token: null });
    apiMock.api.mockResolvedValueOnce(user);
    await loginMfa("m", "123456");
    expect(apiMock.api).toHaveBeenNthCalledWith(1, "/api/auth/login/mfa", "POST", { mfa_token: "m", code: "123456" });
    expect(apiMock.setAccessToken).toHaveBeenCalledWith("t2");
    expect(session.user).toEqual(user);
  });
});

describe("logout", () => {
  it("clears local state even if the server call fails", async () => {
    session.user = user;
    apiMock.api.mockRejectedValue(new Error("offline"));
    await expect(logout()).rejects.toThrow("offline");
    expect(apiMock.setAccessToken).toHaveBeenCalledWith(null);
    expect(session.user).toBeNull();
  });

  it("revokes the session on the server", async () => {
    session.user = user;
    apiMock.api.mockResolvedValue(undefined);
    await logout();
    expect(apiMock.api).toHaveBeenCalledWith("/api/auth/logout", "POST");
    expect(session.user).toBeNull();
  });
});
