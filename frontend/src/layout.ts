export type Layout = "mobile" | "desktop";
export type LayoutChoice = Layout | "auto";

export const LAYOUT_KEY = "einsatzbereit.layout";

/** Media query that marks a phone sized screen. Tablets in portrait count as phones, laptops do not. */
export const MOBILE_QUERY = "(max-width: 760px), (pointer: coarse) and (max-width: 900px)";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function browserStorage(): StorageLike | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Reads the stored layout choice. Unknown values and missing storage mean automatic. */
export function readLayoutChoice(storage: StorageLike | null = browserStorage()): LayoutChoice {
  try {
    const raw = storage?.getItem(LAYOUT_KEY);
    return raw === "mobile" || raw === "desktop" ? raw : "auto";
  } catch {
    return "auto";
  }
}

/** Stores the layout choice. Automatic removes the stored value. */
export function writeLayoutChoice(choice: LayoutChoice, storage: StorageLike | null = browserStorage()): void {
  try {
    if (choice === "auto") storage?.removeItem(LAYOUT_KEY);
    else storage?.setItem(LAYOUT_KEY, choice);
  } catch {
    return;
  }
}

/** Resolves the layout. An explicit choice wins, otherwise the screen size decides. */
export function resolveLayout(choice: LayoutChoice, phoneSized: boolean): Layout {
  if (choice !== "auto") return choice;
  return phoneSized ? "mobile" : "desktop";
}

/** Returns the layout for the current browser. Without matchMedia the desktop layout is used. */
export function currentLayout(
  storage: StorageLike | null = browserStorage(),
  match: ((q: string) => { matches: boolean }) | undefined = globalThis.matchMedia?.bind(globalThis),
): Layout {
  return resolveLayout(readLayoutChoice(storage), match ? match(MOBILE_QUERY).matches : false);
}
