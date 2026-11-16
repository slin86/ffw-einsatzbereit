import { afterEach, describe, expect, it, vi } from "vitest";

import { buzz, dismiss, toast, toasts } from "./toast";

afterEach(() => {
  toasts.splice(0);
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("toast", () => {
  it("shows a message and removes it after the timeout", () => {
    vi.useFakeTimers();
    const vibrate = vi.fn();
    vi.stubGlobal("navigator", { vibrate });
    toast("Gespeichert");
    expect(toasts.map((t) => t.text)).toEqual(["Gespeichert"]);
    expect(vibrate).toHaveBeenCalledWith(12);
    vi.advanceTimersByTime(3200);
    expect(toasts).toHaveLength(0);
  });

  it("keeps at most three messages and does not buzz on errors", () => {
    vi.useFakeTimers();
    const vibrate = vi.fn();
    vi.stubGlobal("navigator", { vibrate });
    for (const t of ["a", "b", "c", "d"]) toast(t, "error");
    expect(toasts.map((t) => t.text)).toEqual(["b", "c", "d"]);
    expect(vibrate).not.toHaveBeenCalled();
  });

  it("dismisses by id and ignores unknown ids", () => {
    const id = toast("x", "ok", 10_000);
    dismiss(999);
    expect(toasts).toHaveLength(1);
    dismiss(id);
    expect(toasts).toHaveLength(0);
  });

  it("survives devices without vibration", () => {
    vi.stubGlobal("navigator", {
      vibrate: () => {
        throw new Error("blocked");
      },
    });
    expect(() => buzz(5)).not.toThrow();
    vi.stubGlobal("navigator", {});
    expect(() => buzz(5)).not.toThrow();
  });
});
