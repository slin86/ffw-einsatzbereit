import { computed, ref, watch, type Ref, type WatchSource } from "vue";

/** Selectable page sizes. Zero means all entries on one page. */
export const PAGE_SIZES = [10, 25, 50, 100, 0];
export const DEFAULT_PAGE_SIZE = 25;
export const AUDIT_LIMITS = [20, 50, 100, 200];
export const DEFAULT_AUDIT_LIMIT = 50;

const PAGE_SIZE_KEY = "einsatzbereit.pageSize";
const AUDIT_LIMIT_KEY = "einsatzbereit.auditLimit";

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function browserStorage(): StorageLike | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Reads a stored number setting. Unknown or unavailable values fall back to the default. */
export function readSetting(
  key: string,
  allowed: readonly number[],
  fallback: number,
  storage: StorageLike | null = browserStorage(),
): number {
  try {
    const raw = storage?.getItem(key);
    return raw != null && allowed.includes(Number(raw)) ? Number(raw) : fallback;
  } catch {
    return fallback;
  }
}

/** Stores a number setting. A browser without storage simply forgets it. */
export function writeSetting(key: string, value: number, storage: StorageLike | null = browserStorage()): void {
  try {
    storage?.setItem(key, String(value));
  } catch {
    return;
  }
}

/** Returns the number of pages. There is always at least one page, and size zero puts everything on one page. */
export function pageCount(total: number, size: number): number {
  return size <= 0 ? 1 : Math.max(1, Math.ceil(total / size));
}

/** Keeps a page number inside the valid range. */
export function clampPage(page: number, total: number, size: number): number {
  return Math.min(Math.max(1, Math.trunc(page) || 1), pageCount(total, size));
}

/** Returns the entries of one page. */
export function pageSlice<T>(items: readonly T[], page: number, size: number): T[] {
  if (size <= 0) return [...items];
  const start = (clampPage(page, items.length, size) - 1) * size;
  return items.slice(start, start + size);
}

/** Returns the first and last position shown on a page, counting from one. An empty list returns zero for both. */
export function pageRange(page: number, total: number, size: number): [number, number] {
  if (total === 0) return [0, 0];
  if (size <= 0) return [1, total];
  const current = clampPage(page, total, size);
  return [(current - 1) * size + 1, Math.min(current * size, total)];
}

/** Page size shared by all lists. It is remembered in the browser. */
export const pageSize = ref(readSetting(PAGE_SIZE_KEY, PAGE_SIZES, DEFAULT_PAGE_SIZE));

export function setPageSize(size: number): void {
  pageSize.value = PAGE_SIZES.includes(size) ? size : DEFAULT_PAGE_SIZE;
  writeSetting(PAGE_SIZE_KEY, pageSize.value);
}

/** Number of audit entries loaded per request. It is remembered in the browser. */
export const auditLimit = ref(readSetting(AUDIT_LIMIT_KEY, AUDIT_LIMITS, DEFAULT_AUDIT_LIMIT));

export function setAuditLimit(limit: number): void {
  auditLimit.value = AUDIT_LIMITS.includes(limit) ? limit : DEFAULT_AUDIT_LIMIT;
  writeSetting(AUDIT_LIMIT_KEY, auditLimit.value);
}

/**
 * Pages a list that is already loaded. The page goes back to the first one when the page size or the reset source
 * changes, and it stays inside the valid range when the list shrinks.
 */
export function usePaging<T>(items: Readonly<Ref<readonly T[]>>, resetOn?: WatchSource<unknown>) {
  const requested = ref(1);
  const total = computed(() => items.value.length);
  const page = computed(() => clampPage(requested.value, total.value, pageSize.value));
  const count = computed(() => pageCount(total.value, pageSize.value));
  const pageItems = computed(() => pageSlice(items.value, page.value, pageSize.value));

  function setPage(next: number): void {
    requested.value = clampPage(next, total.value, pageSize.value);
  }

  watch(pageSize, () => setPage(1));
  if (resetOn) watch(resetOn, () => setPage(1));

  return { page, count, total, pageItems, setPage };
}
