<script lang="ts">
export type IconName =
  | "board"
  | "badge"
  | "plus"
  | "people"
  | "more"
  | "back"
  | "chevron"
  | "search"
  | "close"
  | "share"
  | "check"
  | "filter"
  | "edit"
  | "trash"
  | "user"
  | "shield"
  | "logout"
  | "screen"
  | "history"
  | "list"
  | "key"
  | "clock";

const PATHS: Record<IconName, string> = {
  board: "M4 4h16v16H4z M8 9h.01 M12 9h.01 M16 9h.01 M8 13h.01 M12 13h.01 M16 13h.01 M8 17h.01 M12 17h.01",
  badge: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z M9 12l2 2 4-4",
  plus: "M12 5v14 M5 12h14",
  people:
    "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6 M16 4.5a3.5 3.5 0 0 1 0 6.5 M21 20c0-2.6-1.6-4.8-4-5.6",
  more: "M4 7h16 M4 12h16 M4 17h16",
  back: "M15 5l-7 7 7 7",
  chevron: "M9 6l6 6-6 6",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4",
  close: "M6 6l12 12 M18 6L6 18",
  share: "M12 3v12 M7 8l5-5 5 5 M5 13v6h14v-6",
  check: "M5 12.5l4.5 4.5L19 7",
  filter: "M4 6h16 M7 12h10 M10 18h4",
  edit: "M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4",
  trash: "M5 7h14 M10 7V4h4v3 M7 7l1 13h8l1-13",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8",
  shield: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z",
  logout: "M14 4h5v16h-5 M10 8l-4 4 4 4 M6 12h10",
  screen: "M3 5h18v11H3z M8 20h8 M12 16v4",
  history: "M4 12a8 8 0 1 0 2.3-5.6 M4 4v4h4 M12 8v4l3 2",
  list: "M9 6h11 M9 12h11 M9 18h11 M4.5 6h.01 M4.5 12h.01 M4.5 18h.01",
  key: "M15 9a4 4 0 1 1-1.2-2.8 M14 10l7 7v3h-3v-2h-2v-2h-2",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
};
</script>

<script setup lang="ts">
defineProps<{ name: IconName; size?: number }>();
</script>

<template>
  <svg
    class="micon"
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name]" />
  </svg>
</template>

<style scoped>
.micon {
  flex-shrink: 0;
  display: block;
}
</style>
