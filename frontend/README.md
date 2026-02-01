# LoL Coach — Frontend

![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![TypeScript](https://img.shields.io/badge/typescript-strict-blue)
![Next.js](https://img.shields.io/badge/Next.js-16.1-black)
![React](https://img.shields.io/badge/React-19.2-cyan)
![Tailwind](https://img.shields.io/badge/Tailwind-4.0-38bdf8)

A professional-grade, test-driven champion select UI that interfaces with ML services to provide real-time draft recommendations. This project demonstrates **senior-level engineering practices**, including strict type safety, 100% test coverage, and a modern component architecture.
---

## Screenshots

**Draft + Recommendations**
![Draft + Recommendations](images/draft.png)

**Champion Selector**
![Champion Selector](images/championSelector.png)

---

## Hiring Manager: 60-second evaluation

From repo root:

```bash
# Terminal 1 — backend
./run_backend.sh run

# Terminal 2 — frontend
./run_frontend.sh run
````

Open: `http://localhost:3000`

Quality checks (from `frontend/`):

```bash
npm install
npm run lint
npm run typecheck
npm run test -- --coverage
```

What to look for:

* **Strict TypeScript domain model** (`Role`, `Champion`, `Recommendation`, `DraftState`)
* **Custom hooks** isolate state + effects (`useDraft`, `useRecommendations`, `useChampions`, `useSystemStatus`)
* **Integration-style tests** (user flows: pick → ban → reset → recommend) + high coverage
* **Production UX**: loading skeletons, empty states, disabled states, responsive-ish layout

---

## What this frontend does

* Lets you build a partial draft:

  * Allies: picks + bans
  * Enemies: picks + bans
  * Target role (TOP/JUNGLE/MID/ADC/SUPPORT)
* Calls the backend to get **Top-K champion recommendations** for the target role
* Displays:

  * Candidate champions
  * Scores
  * Human-readable reasons (synergy/counter)
  * Extra explanation text (optional, depending on backend)

---

## Architecture at a glance

The UI is intentionally “boring and testable”:

* `app/page.tsx` composes the screen (header, two team columns, center recommendations, selector modal)
* **Hooks hold the logic**, components mostly render:

  * `useDraft` — canonical draft state + slot selection + modal context
  * `useRecommendations` — backend call, loading state, response mapping
  * `useChampions` — DataDragon champion list fetch (for UI images/names)
  * `useSystemStatus` — pings `/health` + `/version` to show backend status in header

### Data flow

1. User clicks a slot → `useDraft` opens `ChampionSelector`
2. User selects champion → `useDraft` updates `DraftState` immutably
3. User clicks “Recommend” → `useRecommendations` POSTs to backend
4. UI renders loading → then `RecommendationCard` list

---

## Tech stack

* Next.js (App Router)
* React + TypeScript (strict)
* Tailwind CSS
* Vitest + React Testing Library

---

## Backend integration

### API contract

**Primary**

* `POST /v1/recommend/draft`

**Utility**

* `GET /health` (system status)
* `GET /version` (artifact/version info)

Example request:

```json
{
  "role": "MID",
  "allies": ["Ahri", "Jinx"],
  "enemies": ["Zed"],
  "bans": ["Yasuo"],
  "top_k": 10
}
```

Example response:

```json
{
  "recommendations": [
    {
      "champion": "Orianna",
      "score": 85,
      "reasons": ["Synergy with Jinx: +4% winrate", "Counters Zed: +2% lane adv"],
      "explanation": "Strong control mage that scales well..."
    }
  ]
}
```

> The frontend is tolerant to “MVP evolution”: the UI layer expects a stable shape (champion + score + reasons), while the backend can improve scoring/explanations over time.

---

## Configuration

### Frontend environment variables

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Default behavior: if `NEXT_PUBLIC_BACKEND_URL` is not set, the frontend uses `http://localhost:8000`.

### Champion data (DataDragon)

Champion metadata and images come from DataDragon. Currently the patch is pinned inside:

* `hooks/useChampions.ts`

If you update the patch, update URLs in that file.

---

## Local development

### Option A: recommended (repo scripts)

From repo root:

```bash
./run_backend.sh run
./run_frontend.sh run
```

### Option B: run frontend standalone

```bash
cd frontend
npm install
npm run dev
```

The app starts on `http://localhost:3000`.

---

## Testing

From `frontend/`:

```bash
npm run test
npm run test -- --coverage
```

Testing philosophy:

* Prefer tests that simulate **real user behavior** (click slot, search champion, select, recommend, reset)
* Keep components small and deterministic so coverage stays high without fragile mocks
* Hooks are tested as “units of behavior,” components as “units of UI contracts”

---

## Project structure

```
frontend/
  app/                 # Next.js entry (layout + page)
  components/
    draft/             # Draft UI (columns, center, cards, selector)
    ui/                # Shared UI atoms (header, icons)
  hooks/               # State + effects (draft, recs, champions, status)
  types/               # Shared TS types
  constants/           # Static config/constants
  tests/               # Mirrors source structure
  images/              # README screenshots / assets
```

---

## Known limitations (honest “not yet”)

* **Small-screen mobile layout**: can break < ~600px (needs responsive refinements)
* **No patch selector in UI**: champion data patch is pinned in `useChampions.ts`
* **No rank selector in UI**: backend supports rank buckets, UI currently does not expose it
* **Global error boundary**: recommended for production hardening

---

## Roadmap (high-signal next steps)

If I extend this project, I’d do:

1. **Patch + rank selectors** (UI → request shaping → backend conditioning)
2. **Error boundary + typed error states** (recoverable vs fatal)
3. **E2E tests** (Playwright): “happy path” + “backend down” + “slow request”
4. **Responsive redesign** for small screens
5. **Caching strategy** (champion list + recommendations) with clear invalidation

---

## Riot / IP disclaimer

LoL Coach is a fan project and is **not endorsed by Riot Games**. League of Legends and Riot Games are trademarks of Riot Games, Inc.

---

## Tiny upgrades that make this README even more “senior”

If you want to push it from “very good” to “unfair”:

1) Add a **“Design decisions”** section (5 bullets max), e.g.
- why hooks over Redux/Zustand
- why strict TS types + enums
- why tests emphasize flows over snapshots
- how you handle loading/error/empty states

2) Add a **“Failure modes”** section:
- backend down → header shows status + UI disables recommend button
- slow backend → skeletons + cancel/retry behavior (if you add it)

3) Add **badges** (even if basic):
- CI
- Coverage
- TypeScript strict
- Lint

4) Add a **1-minute demo GIF** when you eventually have time.

