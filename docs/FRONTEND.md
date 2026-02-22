# Frontend Guide

The frontend is a React + Vite app that visualizes debate results returned by the backend.

## Core files

- `src/App.jsx`: page composition and API orchestration
- `src/api.js`: wrappers for `/api/start`, `/api/state`, `/api/summary`
- `src/components/TopicInput.jsx`: topic form and submit trigger
- `src/components/DebateView.jsx`: round selector, side panels, belief meter
- `src/components/SummaryCard.jsx`: final stats, override controls, image export

---

## UI flow

1. User enters topic and clicks **Start Debate**.
2. Frontend calls `startDebate(topic)`.
3. Backend returns complete state + summary.
4. `DebateView` renders:
   - topic,
   - optional API facts badge,
   - round selector,
   - Pro and Con argument cards,
   - belief meter and winner.
5. `SummaryCard` renders when winner exists.
6. User can:
   - override audience (Pro/Neutral/Con/reset),
   - download summary card as PNG.

---

## Audience override behavior

- Override updates local display immediately.
- It also posts override value to backend summary endpoint.
- If backend request fails, UI intentionally fails silently and keeps local display.

---

## Styling

- Tailwind utility classes with slate/teal/amber palette.
- Responsive layout via simple breakpoint classes.
- No external component library.

---

## Build and run

### Development

```bash
npm run dev
```

### Production build

```bash
npm run build
npm run preview
```

---

## Extension ideas

- add loading skeletons for debate sections,
- add timeline graph of belief history,
- visualize pruning logs in a collapsible panel,
- add persisted user settings for max rounds and theme.

