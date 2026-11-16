import { reactive } from "vue";

export type ToastKind = "ok" | "error";

export interface Toast {
  id: number;
  text: string;
  kind: ToastKind;
}

export const toasts = reactive<Toast[]>([]);
let nextId = 1;

/** Shows a short message at the bottom of the screen and removes it after the given time. */
export function toast(text: string, kind: ToastKind = "ok", ms = 3200): number {
  const id = nextId++;
  toasts.push({ id, text, kind });
  if (toasts.length > 3) toasts.splice(0, toasts.length - 3);
  setTimeout(() => dismiss(id), ms);
  if (kind === "ok") buzz(12);
  return id;
}

export function dismiss(id: number): void {
  const i = toasts.findIndex((t) => t.id === id);
  if (i >= 0) toasts.splice(i, 1);
}

/** Gives short haptic feedback where the device supports it. */
export function buzz(ms: number): void {
  try {
    globalThis.navigator?.vibrate?.(ms);
  } catch {
    return;
  }
}
