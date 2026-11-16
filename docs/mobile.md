# Mobile app

The frontend ships two layouts that share the API client, session, filters and status logic:

- **Desktop** (`src/App.vue`, `src/views/`) – unchanged, full matrix, filters and exports.
- **Mobile** (`src/mobile/`) – a separate, phone-first shell with its own screens.

`src/layout.ts` picks the layout once at start-up: a stored choice (`einsatzbereit.layout` in
`localStorage`) wins, otherwise the media query `MOBILE_QUERY` decides. Users switch under
*Mehr → Ansicht* (mobile) or *Mein Konto → Ansicht* (desktop); the page reloads afterwards.
Both layouts use the same URLs (`src/router.ts`), so password-reset links and shared filter links
work in either layout. Login, password reset, account and the admin pages are reused from the
desktop app inside the mobile shell; their dialogs are styled as bottom sheets by
`src/mobile/mobile.css`.

## Navigation

Bottom tab bar, modelled on native iOS/Android apps: **Lage · Nachweise · (+) Erfassen ·
Kameraden · Mehr**. The raised centre button starts the record flow from anywhere. Pages use
large titles that collapse into the bar on scroll, pull-to-refresh, skeleton loading and toasts
with haptic feedback.

## Journeys

1. **"Are we ready to turn out?"** – *Lage* (`/`). Headline "26 von 50 einsatzbereit" and a peg
   board with one peg per member (green ready, yellow due soon, empty red frame not ready).
   Position chips narrow the board. Tap a peg to open the member.
2. **"Fix what is open"** – *Lage → Zu erledigen*. Segments *Dringend / Bald fällig / Alle*. Every
   open item has an *Eintragen* button that opens a bottom sheet with the member and
   certification already set: one tap for today, one more to save.
3. **"Record an exercise for the whole group"** – *Erfassen* (`/erfassen`), three steps with the
   step in the URL so the phone's back button works: what (recently used first) → who (search,
   "only who needs it", select all) → when (Heute / Gestern / date) → confirmation.
4. **"Who is missing certification X?"** – *Nachweise* (`/uebersicht`) lists certifications with a
   status bar, most urgent first. The detail (`/uebersicht/:id`) groups members by status;
   *Auswählen* or *Alle Offenen auswählen* hands the selection to the record flow
   (`/erfassen?nachweis=…&kameraden=…`), which then only asks for the date.
5. **"Check one member"** – *Kameraden* with search, position chips, letter index and status
   avatars. The member page shows a readiness banner, required certifications (tap to record),
   history (tap an entry to see details or delete it) and the change log.
6. **"Send the list to the Wehrführung"** – the share icon on *Lage*, *Nachweise* and a
   certification opens the device share sheet with a PDF, Excel or CSV export of exactly that
   selection (falls back to a download).
7. **Admin and account** – *Mehr*: profile, password and 2FA, admin pages, layout switch, logout.

## Code

| Path | Purpose |
|---|---|
| `src/layout.ts` | layout choice and detection (tested) |
| `src/mobile/readiness.ts` | readiness, segments, per-certification stats, grouping, texts (tested) |
| `src/mobile/toast.ts` | toasts and haptic feedback (tested) |
| `src/api.ts` `shareFile` | export through the Web Share API with download fallback (tested) |
| `src/mobile/components/` | app bar, bottom sheet, peg board, segmented control, sheets |
| `src/mobile/views/` | Lage, Nachweise, Nachweis, Erfassen, Kameraden, Kamerad, Mehr |
