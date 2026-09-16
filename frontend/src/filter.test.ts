import { describe, expect, it } from "vitest";

import { filterToPairs, filterToQuery, filterToSearch, parseFilter, type MatrixFilter } from "./filter";

const empty: MatrixFilter = {
  q: "",
  position_id: null,
  certification_id: null,
  status: [],
  include_inactive: false,
  only_open: false,
};

describe("parseFilter", () => {
  it("returns defaults for an empty query", () => {
    expect(parseFilter({})).toEqual(empty);
  });

  it("reads all supported parameters", () => {
    expect(
      parseFilter({
        q: "Voß",
        position_id: "3",
        certification_id: "12",
        status: ["expired", "missing"],
        include_inactive: "true",
        only_open: "true",
      }),
    ).toEqual({
      q: "Voß",
      position_id: 3,
      certification_id: 12,
      status: ["missing", "expired"],
      include_inactive: true,
      only_open: true,
    });
  });

  it("accepts a single status as string", () => {
    expect(parseFilter({ status: "valid" }).status).toEqual(["valid"]);
  });

  it("ignores malformed and unknown values", () => {
    const f = parseFilter({
      position_id: "abc",
      certification_id: "-1",
      status: ["bogus", null, "expiring"],
      include_inactive: "yes",
      only_open: ["true", "false"],
    });
    expect(f.position_id).toBeNull();
    expect(f.certification_id).toBeNull();
    expect(f.status).toEqual(["expiring"]);
    expect(f.include_inactive).toBe(false);
    expect(f.only_open).toBe(true);
  });

  it("does not trim the search while typing", () => {
    expect(parseFilter({ q: "Al " }).q).toBe("Al ");
  });
});

describe("serialisation", () => {
  it("omits defaults", () => {
    expect(filterToPairs(empty)).toEqual([]);
    expect(filterToSearch(empty)).toBe("");
    expect(filterToQuery({ ...empty, q: "   " })).toEqual({});
  });

  it("repeats status and trims the search", () => {
    const f: MatrixFilter = { ...empty, q: " Müller ", status: ["missing", "expiring"], position_id: 0 };
    expect(filterToQuery(f)).toEqual({ q: "Müller", position_id: "0", status: ["missing", "expiring"] });
    expect(filterToSearch(f)).toBe("q=M%C3%BCller&position_id=0&status=missing&status=expiring");
  });

  it("round-trips through the URL query", () => {
    const f: MatrixFilter = {
      q: "Anna",
      position_id: 2,
      certification_id: 5,
      status: ["expired", "valid"],
      include_inactive: true,
      only_open: true,
    };
    expect(parseFilter(filterToQuery(f))).toEqual(f);
  });
});

describe("useMatrixFilter", () => {
  async function setup(path: string) {
    const { createApp, defineComponent } = await import("vue");
    const { createMemoryHistory, createRouter } = await import("vue-router");
    const { useMatrixFilter } = await import("./filter");
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/uebersicht", component: defineComponent({ render: () => null }) }],
    });
    const app = createApp({ render: () => null });
    app.use(router);
    await router.push(path);
    await router.isReady();
    const state = app.runWithContext(() => useMatrixFilter());
    return { router, state };
  }

  it("reads the filter from the current route", async () => {
    const { state } = await setup("/uebersicht?only_open=true&status=expired");
    expect(state.filter.value.only_open).toBe(true);
    expect(state.queryString.value).toBe("status=expired&only_open=true");
  });

  it("updates and resets the URL", async () => {
    const { router, state } = await setup("/uebersicht?q=Anna");
    state.update({ position_id: 4 });
    await new Promise((r) => setTimeout(r));
    expect(router.currentRoute.value.query).toEqual({ q: "Anna", position_id: "4" });
    expect(state.filter.value.position_id).toBe(4);
    state.reset();
    await new Promise((r) => setTimeout(r));
    expect(router.currentRoute.value.query).toEqual({});
    expect(state.queryString.value).toBe("");
  });
});
