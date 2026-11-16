import { describe, expect, it } from "vitest";

import { currentLayout, LAYOUT_KEY, MOBILE_QUERY, readLayoutChoice, resolveLayout, writeLayoutChoice } from "./layout";

function memory(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
  };
}

const broken = {
  getItem: () => {
    throw new Error("blocked");
  },
  setItem: () => {
    throw new Error("blocked");
  },
  removeItem: () => {
    throw new Error("blocked");
  },
};

describe("layout choice", () => {
  it("reads stored values and falls back to auto", () => {
    expect(readLayoutChoice(memory({ [LAYOUT_KEY]: "mobile" }))).toBe("mobile");
    expect(readLayoutChoice(memory({ [LAYOUT_KEY]: "desktop" }))).toBe("desktop");
    expect(readLayoutChoice(memory({ [LAYOUT_KEY]: "tablet" }))).toBe("auto");
    expect(readLayoutChoice(memory())).toBe("auto");
    expect(readLayoutChoice(null)).toBe("auto");
    expect(readLayoutChoice(broken)).toBe("auto");
  });

  it("writes and clears the choice", () => {
    const s = memory();
    writeLayoutChoice("desktop", s);
    expect(s.data.get(LAYOUT_KEY)).toBe("desktop");
    writeLayoutChoice("auto", s);
    expect(s.data.has(LAYOUT_KEY)).toBe(false);
    expect(() => writeLayoutChoice("mobile", broken)).not.toThrow();
    expect(() => writeLayoutChoice("mobile", null)).not.toThrow();
  });

  it("resolves explicit choices before the screen size", () => {
    expect(resolveLayout("mobile", false)).toBe("mobile");
    expect(resolveLayout("desktop", true)).toBe("desktop");
    expect(resolveLayout("auto", true)).toBe("mobile");
    expect(resolveLayout("auto", false)).toBe("desktop");
  });

  it("asks the media query when nothing is stored", () => {
    const seen: string[] = [];
    const phone = (q: string) => (seen.push(q), { matches: true });
    expect(currentLayout(memory(), phone)).toBe("mobile");
    expect(seen).toEqual([MOBILE_QUERY]);
    expect(currentLayout(memory({ [LAYOUT_KEY]: "desktop" }), phone)).toBe("desktop");
    expect(currentLayout(memory(), undefined)).toBe("desktop");
  });
});
