import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

import type { User } from "./types";

type GuardTarget = Pick<RouteLocationNormalized, "meta" | "fullPath">;

/** Decides whether a navigation may proceed, given the logged-in user (or null). */
export function accessGuard(to: GuardTarget, user: User | null): true | RouteLocationRaw {
  if (to.meta.public) return true;
  if (!user) return { path: "/login", query: { next: to.fullPath } };
  if (to.meta.admin && user.role !== "admin") return "/";
  return true;
}

/** Only same-site relative paths are accepted as redirect targets after login. */
export function safeNext(next: unknown): string {
  return typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}
