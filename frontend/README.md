# Frontend - LoL Draft Coach

Next.js/React UI with progressive loading and premium UX.

## Quick Start

```bash
./run_frontend.sh        # Run tests + start dev server (http://localhost:3000)
./run_frontend.sh test   # Tests only
./run_frontend.sh fix    # Auto-fix linting
```

## Architecture

```
app/                     # Next.js App Router
components/
├── draft/               # Draft board components
│   ├── RecommendationCard.tsx  # Expandable cards with click-to-expand
│   ├── DraftCenter.tsx
│   ├── TeamColumn.tsx
│   └── ...
└── ui/                  # Shared UI components
hooks/
├── useRecommendations.ts  # Progressive loading (recommend → explain)
├── useDraft.ts
└── ...
```

## Key Features

- **100% Test Coverage**: 70 tests, all passing
- **Progressive Loading**: Recommendations appear instantly (~50ms), explanations stream in (~500ms)
- **Expandable Cards**: Click to see full AI explanations
- **Loading States**: Smooth skeleton animations with "Analyzing strategies..." feedback
- **Type Safety**: Full TypeScript coverage
- **Premium UX**: Glassmorphism, micro-animations, hover effects

## How Progressive Loading Works

1. User clicks "Predict"
2. Frontend calls `/v1/recommend/draft` → recommendations appear instantly
3. Frontend calls `/v1/explain/draft` in background → explanations stream in
4. UI updates automatically when explanations arrive

No blocking, no waiting! ⚡

## Environment Variables

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Backend API URL
```
