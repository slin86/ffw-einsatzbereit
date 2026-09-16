import { computed } from "vue";
import { type LocationQuery, useRoute, useRouter } from "vue-router";

import type { CellStatus } from "./types";

export interface MatrixFilter {
  q: string;
  position_id: number | null;
  certification_id: number | null;
  status: CellStatus[];
  include_inactive: boolean;
  only_open: boolean;
}

export const EMPTY_FILTER: Readonly<MatrixFilter> = {
  q: "",
  position_id: null,
  certification_id: null,
  status: [],
  include_inactive: false,
  only_open: false,
};

const STATUSES: readonly CellStatus[] = ["missing", "expired", "expiring", "valid", "not_required"];

function first(value: LocationQuery[string]): string | null {
  const v = Array.isArray(value) ? value[0] : value;
  return typeof v === "string" ? v : null;
}

function toId(value: LocationQuery[string]): number | null {
  const v = first(value);
  if (v === null || !/^\d+$/.test(v)) return null;
  return Number(v);
}

/** Reads a filter from URL query parameters; unknown or malformed values are ignored. */
export function parseFilter(query: LocationQuery): MatrixFilter {
  const raw = query.status === undefined ? [] : Array.isArray(query.status) ? query.status : [query.status];
  const status = STATUSES.filter((s) => raw.includes(s));
  return {
    q: first(query.q) ?? "",
    position_id: toId(query.position_id),
    certification_id: toId(query.certification_id),
    status,
    include_inactive: first(query.include_inactive) === "true",
    only_open: first(query.only_open) === "true",
  };
}

/** Key/value pairs in a stable order; default values are omitted. */
export function filterToPairs(f: MatrixFilter): [string, string][] {
  const pairs: [string, string][] = [];
  if (f.q.trim()) pairs.push(["q", f.q.trim()]);
  if (f.position_id !== null) pairs.push(["position_id", String(f.position_id)]);
  if (f.certification_id !== null) pairs.push(["certification_id", String(f.certification_id)]);
  for (const s of f.status) pairs.push(["status", s]);
  if (f.include_inactive) pairs.push(["include_inactive", "true"]);
  if (f.only_open) pairs.push(["only_open", "true"]);
  return pairs;
}

export function filterToQuery(f: MatrixFilter): Record<string, string | string[]> {
  const out: Record<string, string | string[]> = {};
  for (const [k, v] of filterToPairs(f)) {
    const cur = out[k];
    out[k] = cur === undefined ? v : Array.isArray(cur) ? [...cur, v] : [cur, v];
  }
  return out;
}

export function filterToSearch(f: MatrixFilter): string {
  return new URLSearchParams(filterToPairs(f)).toString();
}

/** Filter state lives in the URL, so views are shareable and exports use exactly what is shown. */
export function useMatrixFilter() {
  const route = useRoute();
  const router = useRouter();

  const filter = computed<MatrixFilter>(() => parseFilter(route.query));

  function update(patch: Partial<MatrixFilter>): void {
    void router.replace({ query: filterToQuery({ ...filter.value, ...patch }) });
  }

  function reset(): void {
    void router.replace({ query: {} });
  }

  const queryString = computed(() => filterToSearch(filter.value));

  return { filter, update, reset, queryString };
}
