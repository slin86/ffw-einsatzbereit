import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

import type { User } from "./types";

type GuardTarget = Pick<RouteLocationNormalized, "meta" | "fullPath">;

/**
 * Decides whether a navigation may continue. Anonymous users are sent to the login with the requested path, users
 * without admin role are sent to the start page when they open admin pages.
 */
export function accessGuard(to: GuardTarget, user: User | null): true | RouteLocationRaw {
  if (to.meta.public) return true;
  if (!user) return { path: "/login", query: { next: to.fullPath } };
  if (to.meta.admin && user.role !== "admin") return "/";
  return true;
}

/**
 * Returns the redirect target after login. Only relative paths on this site are accepted, anything else leads to the
 * start page, which prevents open redirects.
 */
export function safeNext(next: unknown): string {
  return typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}
