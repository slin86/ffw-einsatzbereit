import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";

import {
  AUDIT_LIMITS,
  DEFAULT_AUDIT_LIMIT,
  DEFAULT_PAGE_SIZE,
  auditLimit,
  clampPage,
  pageCount,
  pageRange,
  pageSize,
  pageSlice,
  readSetting,
  setAuditLimit,
  setPageSize,
  usePaging,
  writeSetting,
} from "./paging";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = { ...initial };
  return {
    getItem: (k: string) => data[k] ?? null,
    setItem: (k: string, v: string) => {
      data[k] = v;
    },
    data,
  };
}

describe("pageCount", () => {
  it("rounds up and is at least one", () => {
    expect(pageCount(0, 10)).toBe(1);
    expect(pageCount(10, 10)).toBe(1);
    expect(pageCount(11, 10)).toBe(2);
    expect(pageCount(95, 10)).toBe(10);
  });

  it("puts everything on one page for size zero", () => {
    expect(pageCount(500, 0)).toBe(1);
  });
});

describe("clampPage", () => {
  it("keeps the page inside the range", () => {
    expect(clampPage(0, 30, 10)).toBe(1);
    expect(clampPage(-4, 30, 10)).toBe(1);
    expect(clampPage(2, 30, 10)).toBe(2);
    expect(clampPage(9, 30, 10)).toBe(3);
    expect(clampPage(Number.NaN, 30, 10)).toBe(1);
    expect(clampPage(2.7, 30, 10)).toBe(2);
  });
});

describe("pageSlice", () => {
  const items = Array.from({ length: 25 }, (_, i) => i + 1);

  it("returns one page", () => {
    expect(pageSlice(items, 1, 10)).toEqual(items.slice(0, 10));
    expect(pageSlice(items, 3, 10)).toEqual([21, 22, 23, 24, 25]);
  });

  it("returns the last page for a page that is too high", () => {
    expect(pageSlice(items, 99, 10)).toEqual([21, 22, 23, 24, 25]);
  });

  it("returns a copy of everything for size zero", () => {
    const all = pageSlice(items, 2, 0);
    expect(all).toEqual(items);
    expect(all).not.toBe(items);
  });

  it("returns nothing for an empty list", () => {
    expect(pageSlice([], 1, 10)).toEqual([]);
  });
});

describe("pageRange", () => {
  it("counts from one", () => {
    expect(pageRange(1, 25, 10)).toEqual([1, 10]);
    expect(pageRange(3, 25, 10)).toEqual([21, 25]);
  });

  it("handles empty lists and size zero", () => {
    expect(pageRange(1, 0, 10)).toEqual([0, 0]);
    expect(pageRange(1, 25, 0)).toEqual([1, 25]);
  });
});

describe("settings", () => {
  it("reads a stored value that is allowed", () => {
    expect(readSetting("k", [10, 25], 25, memoryStorage({ k: "10" }))).toBe(10);
  });

  it("falls back for missing, unknown or broken values", () => {
    expect(readSetting("k", [10, 25], 25, memoryStorage())).toBe(25);
    expect(readSetting("k", [10, 25], 25, memoryStorage({ k: "7" }))).toBe(25);
    expect(readSetting("k", [10, 25], 25, memoryStorage({ k: "abc" }))).toBe(25);
    expect(readSetting("k", [10, 25], 25, null)).toBe(25);
    const broken = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readSetting("k", [10, 25], 25, broken)).toBe(25);
    expect(() => writeSetting("k", 10, broken)).not.toThrow();
  });

  it("writes a value", () => {
    const storage = memoryStorage();
    writeSetting("k", 50, storage);
    expect(storage.data.k).toBe("50");
    expect(() => writeSetting("k", 50, null)).not.toThrow();
  });

  it("accepts only known page sizes and audit limits", () => {
    setPageSize(50);
    expect(pageSize.value).toBe(50);
    setPageSize(0);
    expect(pageSize.value).toBe(0);
    setPageSize(7);
    expect(pageSize.value).toBe(DEFAULT_PAGE_SIZE);
    setAuditLimit(AUDIT_LIMITS[2]!);
    expect(auditLimit.value).toBe(100);
    setAuditLimit(3);
    expect(auditLimit.value).toBe(DEFAULT_AUDIT_LIMIT);
  });
});

describe("usePaging", () => {
  it("pages a list and follows the page size", async () => {
    setPageSize(10);
    const items = ref(Array.from({ length: 25 }, (_, i) => i + 1));
    const paging = usePaging(items);
    expect(paging.count.value).toBe(3);
    expect(paging.pageItems.value).toHaveLength(10);
    paging.setPage(3);
    expect(paging.pageItems.value).toEqual([21, 22, 23, 24, 25]);
    setPageSize(25);
    await nextTick();
    expect(paging.page.value).toBe(1);
    expect(paging.pageItems.value).toHaveLength(25);
  });

  it("goes back to the first page when the reset source changes", async () => {
    setPageSize(10);
    const items = ref(Array.from({ length: 25 }, (_, i) => i + 1));
    const query = ref("a");
    const paging = usePaging(items, query);
    paging.setPage(2);
    expect(paging.page.value).toBe(2);
    query.value = "b";
    await nextTick();
    expect(paging.page.value).toBe(1);
  });

  it("stays on a valid page when the list shrinks", () => {
    setPageSize(10);
    const items = ref(Array.from({ length: 25 }, (_, i) => i + 1));
    const paging = usePaging(items);
    paging.setPage(3);
    items.value = items.value.slice(0, 12);
    expect(paging.page.value).toBe(2);
    expect(paging.pageItems.value).toEqual([11, 12]);
    items.value = [];
    expect(paging.page.value).toBe(1);
    expect(paging.pageItems.value).toEqual([]);
  });
});
