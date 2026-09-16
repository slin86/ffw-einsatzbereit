import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./styles.css";

import { createApp } from "vue";

import { setAuthLostHandler } from "./api";
import App from "./App.vue";
import { router } from "./router";
import { restoreSession, session } from "./session";

setAuthLostHandler(() => {
  session.user = null;
  if (!router.currentRoute.value.meta.public) {
    void router.push({ path: "/login", query: { next: router.currentRoute.value.fullPath } });
  }
});

if ("serviceWorker" in navigator) {
  void navigator.serviceWorker.register("/sw.js").catch(() => {});
}

void restoreSession().then(() => createApp(App).use(router).mount("#app"));
