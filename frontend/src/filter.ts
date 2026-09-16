import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { CellStatus } from "./types";

export interface MatrixFilter {
  q: string;
  position_id: number | null;
  certification_id: number | null;
  status: CellStatus[];
  include_inactive: boolean;
  only_open: boolean;
}

/** Filter state lives in the URL, so views are shareable and exports use exactly what is shown. */
export function useMatrixFilter() {
  const route = useRoute();
  const router = useRouter();

  const filter = computed<MatrixFilter>(() => {
    const q = route.query;
    const num = (v: unknown) => (typeof v === "string" && v !== "" ? Number(v) : null);
    const status = q.status === undefined ? [] : Array.isArray(q.status) ? q.status : [q.status];
    return {
      q: typeof q.q === "string" ? q.q : "",
      position_id: num(q.position_id),
      certification_id: num(q.certification_id),
      status: status.filter((s): s is CellStatus => typeof s === "string"),
      include_inactive: q.include_inactive === "true",
      only_open: q.only_open === "true",
    };
  });

  function update(patch: Partial<MatrixFilter>): void {
    void router.replace({ query: toQuery({ ...filter.value, ...patch }) });
  }

  function reset(): void {
    void router.replace({ query: {} });
  }

  const queryString = computed(() => new URLSearchParams(toPairs(filter.value)).toString());

  return { filter, update, reset, queryString };
}

function toPairs(f: MatrixFilter): [string, string][] {
  const pairs: [string, string][] = [];
  if (f.q.trim()) pairs.push(["q", f.q.trim()]);
  if (f.position_id !== null) pairs.push(["position_id", String(f.position_id)]);
  if (f.certification_id !== null) pairs.push(["certification_id", String(f.certification_id)]);
  for (const s of f.status) pairs.push(["status", s]);
  if (f.include_inactive) pairs.push(["include_inactive", "true"]);
  if (f.only_open) pairs.push(["only_open", "true"]);
  return pairs;
}

function toQuery(f: MatrixFilter): Record<string, string | string[]> {
  const out: Record<string, string | string[]> = {};
  for (const [k, v] of toPairs(f)) {
    const cur = out[k];
    out[k] = cur === undefined ? v : Array.isArray(cur) ? [...cur, v] : [cur, v];
  }
  return out;
}
