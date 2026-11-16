import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from "vue-router";

import { accessGuard } from "./guard";
import type { Layout } from "./layout";
import { session } from "./session";

declare module "vue-router" {
  interface RouteMeta {
    public?: boolean;
    admin?: boolean;
    title?: string;
    /** Tab of the mobile layout that is highlighted. */
    tab?: "lage" | "nachweise" | "kameraden" | "mehr";
    /** Parent page for the back button of the mobile layout. */
    back?: string;
    /** Hides the tab bar of the mobile layout, for flows that need the whole screen. */
    immersive?: boolean;
    /** Desktop page shown inside the mobile layout, which then adds its own back bar. */
    reused?: boolean;
  }
}

const memberId = (r: { params: Record<string, unknown> }) => ({ id: Number(r.params.id) });

const publicRoutes: RouteRecordRaw[] = [
  { path: "/login", component: () => import("./views/LoginView.vue"), meta: { public: true, title: "Anmelden" } },
  {
    path: "/passwort-vergessen",
    component: () => import("./views/ForgotView.vue"),
    meta: { public: true, title: "Passwort vergessen" },
  },
  {
    path: "/passwort-neu",
    component: () => import("./views/ResetView.vue"),
    meta: { public: true, title: "Neues Passwort" },
  },
];

function adminRoutes(back?: string): RouteRecordRaw[] {
  return [
    {
      path: "/admin/nachweise",
      component: () => import("./views/admin/CertificationsView.vue"),
      meta: { admin: true, title: "Nachweise", back, tab: back ? "mehr" : undefined, reused: !!back },
    },
    {
      path: "/admin/funktionen",
      component: () => import("./views/admin/PositionsView.vue"),
      meta: { admin: true, title: "Funktionen", back, tab: back ? "mehr" : undefined, reused: !!back },
    },
    {
      path: "/admin/benutzer",
      component: () => import("./views/admin/UsersView.vue"),
      meta: { admin: true, title: "Benutzer", back, tab: back ? "mehr" : undefined, reused: !!back },
    },
    {
      path: "/admin/protokoll",
      component: () => import("./views/admin/AuditView.vue"),
      meta: { admin: true, title: "Protokoll", back, tab: back ? "mehr" : undefined, reused: !!back },
    },
  ];
}

const desktopRoutes: RouteRecordRaw[] = [
  ...publicRoutes,
  { path: "/", component: () => import("./views/TodoView.vue"), meta: { title: "Offen" } },
  { path: "/uebersicht", component: () => import("./views/BoardView.vue"), meta: { title: "Übersicht" } },
  { path: "/erfassen", component: () => import("./views/BulkView.vue"), meta: { title: "Erfassen" } },
  { path: "/kameraden", component: () => import("./views/MembersView.vue"), meta: { title: "Kameraden" } },
  {
    path: "/kameraden/:id(\\d+)",
    component: () => import("./views/MemberView.vue"),
    props: memberId,
    meta: { title: "Kamerad" },
  },
  { path: "/konto", component: () => import("./views/AccountView.vue"), meta: { title: "Mein Konto" } },
  ...adminRoutes(),
  {
    path: "/uebersicht/:id(\\d+)",
    redirect: (to) => ({ path: "/uebersicht", query: { certification_id: to.params.id } }),
  },
  { path: "/mehr", redirect: "/konto" },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

/** Same paths as the desktop layout, so links from mails and shared filters work in both layouts. */
const mobileRoutes: RouteRecordRaw[] = [
  ...publicRoutes,
  { path: "/", component: () => import("./mobile/views/HomeView.vue"), meta: { title: "Lage", tab: "lage" } },
  {
    path: "/uebersicht",
    component: () => import("./mobile/views/CertsView.vue"),
    meta: { title: "Nachweise", tab: "nachweise" },
  },
  {
    path: "/uebersicht/:id(\\d+)",
    component: () => import("./mobile/views/CertView.vue"),
    props: memberId,
    meta: { title: "Nachweis", tab: "nachweise", back: "/uebersicht" },
  },
  {
    path: "/erfassen",
    component: () => import("./mobile/views/RecordView.vue"),
    meta: { title: "Erfassen", immersive: true },
  },
  {
    path: "/kameraden",
    component: () => import("./mobile/views/MembersView.vue"),
    meta: { title: "Kameraden", tab: "kameraden" },
  },
  {
    path: "/kameraden/:id(\\d+)",
    component: () => import("./mobile/views/MemberView.vue"),
    props: memberId,
    meta: { title: "Kamerad", tab: "kameraden", back: "/kameraden" },
  },
  { path: "/mehr", component: () => import("./mobile/views/MoreView.vue"), meta: { title: "Mehr", tab: "mehr" } },
  {
    path: "/konto",
    component: () => import("./views/AccountView.vue"),
    meta: { title: "Mein Konto", tab: "mehr", back: "/mehr", reused: true },
  },
  ...adminRoutes("/mehr"),
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

export function createAppRouter(layout: Layout): Router {
  const router = createRouter({
    history: createWebHistory(),
    routes: layout === "mobile" ? mobileRoutes : desktopRoutes,
    scrollBehavior: layout === "mobile" ? (_to, _from, saved) => saved ?? { top: 0 } : undefined,
  });

  router.beforeEach((to) => accessGuard(to, session.user));

  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} · Einsatzbereit` : "Einsatzbereit";
  });

  return router;
}
