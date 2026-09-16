import { createRouter, createWebHistory } from "vue-router";

import { session } from "./session";

declare module "vue-router" {
  interface RouteMeta {
    public?: boolean;
    admin?: boolean;
    title?: string;
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("./views/LoginView.vue"), meta: { public: true, title: "Anmelden" } },
    { path: "/passwort-vergessen", component: () => import("./views/ForgotView.vue"), meta: { public: true, title: "Passwort vergessen" } },
    { path: "/passwort-neu", component: () => import("./views/ResetView.vue"), meta: { public: true, title: "Neues Passwort" } },
    { path: "/", component: () => import("./views/TodoView.vue"), meta: { title: "Offen" } },
    { path: "/uebersicht", component: () => import("./views/BoardView.vue"), meta: { title: "Übersicht" } },
    { path: "/erfassen", component: () => import("./views/BulkView.vue"), meta: { title: "Erfassen" } },
    { path: "/kameraden", component: () => import("./views/MembersView.vue"), meta: { title: "Kameraden" } },
    { path: "/kameraden/:id(\\d+)", component: () => import("./views/MemberView.vue"), props: (r) => ({ id: Number(r.params.id) }), meta: { title: "Kamerad" } },
    { path: "/konto", component: () => import("./views/AccountView.vue"), meta: { title: "Mein Konto" } },
    { path: "/admin/nachweise", component: () => import("./views/admin/CertificationsView.vue"), meta: { admin: true, title: "Nachweise" } },
    { path: "/admin/funktionen", component: () => import("./views/admin/PositionsView.vue"), meta: { admin: true, title: "Funktionen" } },
    { path: "/admin/benutzer", component: () => import("./views/admin/UsersView.vue"), meta: { admin: true, title: "Benutzer" } },
    { path: "/admin/protokoll", component: () => import("./views/admin/AuditView.vue"), meta: { admin: true, title: "Protokoll" } },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  if (to.meta.public) return true;
  if (!session.user) return { path: "/login", query: { next: to.fullPath } };
  if (to.meta.admin && session.user.role !== "admin") return "/";
  return true;
});

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Einsatzbereit` : "Einsatzbereit";
});
