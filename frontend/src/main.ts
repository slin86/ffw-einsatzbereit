import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./styles.css";

import { type Component, createApp } from "vue";

import { setAuthLostHandler } from "./api";
import { currentLayout } from "./layout";
import { createAppRouter } from "./router";
import { restoreSession, session } from "./session";

const layout = currentLayout();
document.documentElement.dataset.layout = layout;
const router = createAppRouter(layout);

setAuthLostHandler(() => {
  session.user = null;
  if (!router.currentRoute.value.meta.public) {
    void router.push({ path: "/login", query: { next: router.currentRoute.value.fullPath } });
  }
});

if ("serviceWorker" in navigator) {
  void navigator.serviceWorker.register("/sw.js").catch(() => {});
}

const root: Promise<Component> =
  layout === "mobile"
    ? import("./mobile/MobileApp.vue").then((m) => m.default)
    : import("./App.vue").then((m) => m.default);

void Promise.all([root, restoreSession()]).then(([App]) => createApp(App).use(router).mount("#app"));
