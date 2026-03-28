# PRD — Draft & Build Coach (LoL)

## 1) Summary

**Product:** Draft & Build Coach (LoL)
**One-liner:** Interactive champ select assistant that recommends the next pick **by role** with **transparent synergy/counter reasons**, powered by a real data pipeline and offline evaluation.

**M1 deliverable:** Enter partial draft → get **Top-K** recommendations + **why** + offline metrics in README.

---

## 2) Goals and Non-goals

### Goals (M1)

1. **Draft Recommendations (by role):** Given allies/enemies/picks/bans + role → return **ranked champions**.
2. **Explainability:** For each recommended champ, show:

   * Top synergy edges (ally ↔ candidate)
   * Top counter edges (candidate ↔ enemy)
   * Role strength contribution
3. **Patch + rank awareness:** Stats are partitioned by patch + rank bucket (coarse is fine).
4. **Real offline evaluation:** Compute **Recall@K**, **NDCG@K**, and a basic “score correlates with winrate” sanity check.
5. **API-first:** Backend exposes `POST /api/v1/recommend/draft` (and health/version).
6. **Reproducible pipeline:** One command to ingest a small dataset; one command to train/build aggregates; one command to run API.

### Non-goals (M1)

* No user accounts, payments, subscriptions.
* No real-time lobby detection.
* No full win-probability model (that’s M2).
* No item optimization (later milestone).

---

## 3) Target Users + Core UX

### Primary user

* LoL player who wants “What should I pick next and why?” during champ select.

### UX Flow (M1)

1. User selects:

   * Patch (or default “latest in dataset”)
   * Rank bucket (e.g., IRON–BRONZE, SILVER–GOLD, PLAT–EMERALD, DIAMOND+)
   * Target role (TOP/JUNGLE/MID/ADC/SUPPORT)
2. User inputs ally/enemy picks (and optional bans).
3. Click **Recommend** → results table:

   * champ name, score, top synergy reasons, top counter reasons
   * optional “lock candidate” to simulate “what if we pick this?”

---

## 4) Functional Requirements (M1)

### FR1 — Recommendation

* Input: patch, rank bucket, role, allies, enemies, bans
* Output: top K recommendations with score breakdown and explanation edges

### FR2 — Explanation objects

For each recommendation:

* `score_total`
* `score_components`:

  * `role_strength`
  * `synergy_sum`
  * `counter_sum`
  * `penalties` (pickrate penalty optional)
* `why`:

  * top synergy edges: (ally champ, weight, sample size)
  * top counter edges: (enemy champ, weight, sample size)

### FR3 — Data ingestion pipeline (minimal but real)

* Pull match IDs and match details for chosen patch + rank buckets (or approximate via your current approach).
* Extract from match:

  * patch/version, rank bucket (or tier)
  * team compositions mapped to roles
  * win/loss label
  * picks/bans (bans optional for M1)
* Store as **Parquet** (preferred) or JSONL/CSV (acceptable).

### FR4 — Model building (Bayesian-smoothed stats)

Compute per (patch, rank_bucket):

* Winrate by (champion, role)
* Synergy lift: (ally champ A, champ B, role B)
* Counter lift: (candidate champ B, enemy champ E, role B vs role E optional)
* Store as versioned artifacts (parquet files) used at inference.

### FR5 — Offline evaluation

On held-out drafts:

* **Recall@10**: whether true picked champ appears in top 10.
* **NDCG@10**: ranking quality.
* **Sanity**: bucket by score decile → winrate should generally increase.

### FR6 — API

* `POST /api/v1/recommend/draft`
* `GET /health`
* `GET /version`

---

## 5) Data Requirements

### Draft row (canonical training record)

**Minimum fields:**

* `match_id`
* `patch` (e.g., “14.1” or full)
* `rank_bucket`
* `team_side` (BLUE/RED)
* `role` (for each pick)
* `ally_champs_by_role` (TOP/JG/MID/ADC/SUP)
* `enemy_champs_by_role` (TOP/JG/MID/ADC/SUP)
* `outcome` (win/loss for the team_side)
* `picked_champ_for_role` (the champ you want to treat as the “label” for ranking eval)

**Storage:**

* `data/raw/` for raw pulls
* `data/processed/` for cleaned draft rows
* `data/artifacts/` for computed tables used by inference

### Example dataset for GitHub

To keep your repo lightweight:

* Put **small samples** only:

  * `data/examples/drafts_sample.parquet` (few hundred rows)
  * `data/examples/request_example.json`
  * `data/examples/response_example.json`
* Add `.gitignore` rules to avoid committing full dumps.

---

## 6) System Design (M1)

### High-level architecture

* **Ingest** (offline scripts) → **Processed drafts** (parquet)
* **Train/build** (offline scripts) → **Artifacts** (parquet tables)
* **Inference** (FastAPI) loads artifacts into memory (or caches) → returns recs

### Inference scoring (M1)

For a candidate champ `c` in role `r`:

```
score(c) =
  role_strength(c, r)
  + Σ synergy(ally_i, c, r)
  + Σ counter(c, enemy_j, r)
  - pickrate_penalty(c, r)   # optional
```

Return top K by score, plus the top contributing edges.

---

## 7) Repository Layout (simple + scalable)

Here’s a structure that matches what you described (domain enums, riot accessor, ingest dir, ml dir, api v1):

```
backend/
  app/
    main.py
    api/
      v1/
        router.py
        recommend.py              # POST /recommend/draft
        schemas.py                # request/response models (pydantic)
    domain/
      enums.py                    # Role, RankBucket, TeamSide, Queue, Region
      models.py                   # small shared dataclasses/pydantic models
    riot_accessor/
      client.py                   # thin wrapper around Riot endpoints you use
      rate_limit.py               # retry/backoff, token bucket, etc.
      mappers.py                  # map API payloads -> internal domain objects
    ingest/
      __init__.py
      pull_match_ids.py           # get match ids per rank bucket
      pull_matches.py             # fetch match details by id
      extract_drafts.py           # convert matches -> draft rows
      run_ingest.py               # one CLI entrypoint for ingestion
    ml/
      __init__.py
      build_tables.py             # compute Bayesian-smoothed role/synergy/counter
      scorer.py                   # scoring logic reused by inference + eval
      eval_offline.py             # recall@k, ndcg@k, sanity plots/tables
      artifacts.py                # load/save artifacts; versioning helpers
    data/
      README.md                   # what lives here, how to generate
      examples/
        drafts_sample.parquet
        request_example.json
        response_example.json
    config/
      settings.py                 # env config (paths, keys, rate limits, etc.)
    scripts/
      make_sample_data.py         # optional: create tiny sample for GitHub
  tests/
    api/
      test_recommend.py
    ml/
      test_scorer.py
    ingest/
      test_extract_drafts.py
  pyproject.toml
  README.md
  .env.example
```

### Notes on “where things should be”

* **`domain/`**: only “game concepts” and shared types (Role, RankBucket, TeamSide, etc.) + small shared models.
* **`riot_accessor/`**: only Riot communication + mapping payloads → domain objects. No business logic.
* **`ingest/`**: orchestration + ETL to create `data/processed/drafts_*.parquet`.
* **`ml/`**: artifact building, scoring function, evaluation.
* **`api/`**: request/response schemas + endpoint handlers. Calls `ml/scorer.py` and loads artifacts via `ml/artifacts.py`.

---

## 8) API Specification (M1)

### `POST /api/v1/recommend/draft`

**Request (JSON)**

```json
{
  "patch": "14.1",
  "rank_bucket": "PLAT_EMERALD",
  "role": "MID",
  "allies": {
    "TOP": "Garen",
    "JUNGLE": "LeeSin",
    "MID": null,
    "ADC": "Jinx",
    "SUPPORT": "Thresh"
  },
  "enemies": {
    "TOP": "Darius",
    "JUNGLE": null,
    "MID": null,
    "ADC": null,
    "SUPPORT": null
  },
  "bans": ["Yasuo", "Zed"]
}
```

**Response (JSON)**

```json
{
  "meta": {
    "patch": "14.1",
    "rank_bucket": "PLAT_EMERALD",
    "role": "MID",
    "k": 10,
    "artifact_version": "2026-01-18"
  },
  "recommendations": [
    {
      "champion": "Orianna",
      "score_total": 1.83,
      "score_components": {
        "role_strength": 1.10,
        "synergy_sum": 0.55,
        "counter_sum": 0.25,
        "penalties": -0.07
      },
      "why": {
        "top_synergies": [
          {"with_ally": "Jinx", "lift": 0.18, "n": 12400},
          {"with_ally": "Thresh", "lift": 0.13, "n": 9800}
        ],
        "top_counters": [
          {"vs_enemy": "Darius", "lift": 0.09, "n": 2100}
        ]
      }
    }
  ]
}
```

### `GET /health`

Returns `{ "status": "ok" }`

### `GET /version`

Returns build info + artifact version loaded

---

## 9) ML Artifacts (M1)

### Artifacts produced by `ml/build_tables.py`

Store under `app/data/artifacts/<patch>/<rank_bucket>/`:

* `role_strength.parquet`

  * columns: champion, role, smoothed_winrate, n_games, prior_used
* `synergy.parquet`

  * columns: ally_champ, candidate_champ, role, lift, n_games
* `counter.parquet`

  * columns: enemy_champ, candidate_champ, role, lift, n_games
* `pickrate.parquet` (optional)

  * columns: champion, role, pickrate, n_games

### Bayesian smoothing (simple requirement)

* Use a Beta prior (or equivalent) so low-sample champs don’t spike.
* PRD requirement is **“smoothed, not raw”**; exact formula is implementation detail.

---

## 10) Offline Evaluation (M1)

### Dataset split

* Split by time (match end time) or by match_id hash.
* Ensure held-out set is truly unseen.

### Metrics to report in README

* Recall@10
* NDCG@10
* Optional: slice metrics by rank bucket, patch.

### Acceptance target (non-binding)

* You’re not optimizing for a magic number—just report the real value and show it’s computed correctly.

---

## 11) Operational Requirements (M1)

### Performance

* p50 latency target: < 150ms local for cached artifacts (not strict)
* Must not re-load artifacts per request (load on startup, or use a singleton cache).

### Reliability

* If artifacts missing for (patch, rank_bucket), return a clear 400 with available options.

### Config + Secrets

* `RIOT_API_KEY` via `.env` (never committed)
* data/artifact paths via settings

---

## 12) Compliance / Policy Notes (high-level)

* If you ever make it public-facing, treat Riot API access and monetization as policy-controlled. Keep M1 as local/dev-first and document the constraints in README.

---

## 13) Milestones (Build Plan)

### M0 (scaffold)

* Repo runs end-to-end with mock response
* `/health` works
* FE calls backend

### M1 (resume-ready)

**Ingest**

* `run_ingest.py` produces `data/processed/drafts_<patch>_<rank>.parquet`

**ML**

* `build_tables.py` produces artifacts
* `eval_offline.py` prints metrics

**API**

* `POST /api/v1/recommend/draft` returns real results from artifacts

**Docs**

* System diagram + how to run + metrics in README

---

## 14) Definition of Done (M1)

You can say M1 is “done” when:

1. `make ingest` (or a single command) produces a processed dataset (even small).
2. `make train` produces artifacts.
3. `make serve` runs FastAPI and returns top-K recs with explanations.
4. `make eval` prints Recall@10 and NDCG@10.
5. Repo includes `data/examples/*` and a README demo.

---

## 15) Suggested Makefile / Commands (optional but helpful)

* `make ingest` → runs `app/ingest/run_ingest.py`
* `make train` → runs `app/ml/build_tables.py`
* `make eval` → runs `app/ml/eval_offline.py`
* `make serve` → runs `uvicorn app.main:app --reload`

---




---

# APPENDIX: Original Project Specifications
(The following section contains the original project proposal and milestone definitions for reference)

## Draft & Build Coach (LoL)


Interactive **champ select assistant + item path optimizer** built like a real ML product: data pipeline → offline evaluation → deployed inference → explanations.

### What it does

You give it a **partial draft** (roles + ally/enemy picks/bans), and it returns:

* **Top champion recommendations** (by role) with **synergy/counter reasons**
* **Estimated win-prob delta** for each candidate pick (with uncertainty/calibration later)
* A **plan for the rest of draft** (later milestones: “if they pick X, respond with Y”)
* **Item path suggestions** (start with “most likely / highest winrate next items”; later become state-aware optimization)

### Why it’s a perfect MLE / AI Engineer project

It naturally lets you demonstrate:

* **Data engineering** (Riot API ingestion, rate-limited backfill, patch/versioning)
* **Modeling** (supervised win prediction, recommendation ranking, uncertainty)
* **Decision-making** (bandits/game theory style draft planning; later RL/MDP framing)
* **Product engineering** (FastAPI service, caching, UI, monitoring, eval dashboards)
* **Policy-aware shipping** (free tier + monetization rules; avoid in-game ads) ([developer.riotgames.com][1])

---

## Tech (high-likelihood, shippable)

**Frontend**

* Next.js/React + TypeScript
* Draft board UI (roles, picks/bans, search, patch selector)
* Explain panel (“why this pick”, matchup edges, synergy pairs)

**Backend**

* FastAPI (stateless inference)
* Redis cache (hot queries: popular drafts)
* Postgres (match data + aggregates + model registry metadata)

**ML / Data**

* Ingestion workers (Python): match collection + backfill + patch partitioning
* Feature store (lightweight): parquet + DuckDB/Polars for training
* Models:

  * M1: Bayesian-smoothed stats + simple scorer (fast + interpretable)
  * M2+: LightGBM / logistic regression win predictor
  * Later: embeddings + sequence models; draft search (MCTS/beam)

**Riot constraints you’ll respect**

* If it’s public-facing you’ll need a **production key** (don’t run a public app on a dev key). ([developer.riotgames.com][2])
* You can monetize only if registered/approved/acknowledged and must keep a free tier; **no ads “in-game / loading / client”**. ([developer.riotgames.com][1])
* Plan for rate limits + backoff/Retry-After handling. ([developer.riotgames.com][2])

---

# Milestones (with M1 = resume-ready MVP)

## M0 — Scaffold (1 session)

**Goal:** FE + BE talking; local demo works.
**Deliverables**

* FastAPI: `/health`, `/version`
* Frontend: “Draft board” mock UI + calls backend
* Docker compose (frontend, backend, redis)
* Basic CI: lint + tests

**Solves**

* Nothing “ML” yet, but repo is runnable + clean.

---

## M1 — Resume-worthy MVP (Draft recommender + explanations)

**Goal:** Enter a draft → get top picks + reasons + offline eval numbers.
This is what you put on your resume.

### Deliverables

**Data (minimal but real)**

* A small ingestion pipeline that pulls:

  * match IDs → match details → extract picks/bans/roles/outcome
* Store **a few hundred thousand** drafts (or start smaller and scale)
* Partition by **patch** and **rank tier** (even if coarse)
* **Champion Mapping**:
  * Ingest DataDragon to map Champion IDs to Names/Metadata using `fetch_ddragon.py`.

**Model (baseline that’s impressive because it’s correct + explainable)**

* Build these stats with **Bayesian smoothing** (so low-sample champs don’t lie):

  * Winrate by champion+role
  * **Synergy**: pair lift (ally champ A with ally champ B)
  * **Counter**: matchup lift (champ A vs enemy champ B)
* Draft scoring function (simple, strong, explainable):

  * `score(candidate) = role_strength + Σ synergy(ally, candidate) + Σ counter(candidate, enemy) - pickrate_penalty + comfort(optional)`
* Returns:

  * Top K champs
  * “Why”: top 3 synergy edges + top 3 counters driving score
* **GenAI Explanations**:
  * Use an LLM to generate natural language explanations for the recommendations, providing context on *why* a pick is good (e.g., "Good synergy with X", "Hard counters Y").

**API**

* `POST /v1/recommend/draft`

  * input: patch, rank bucket, role, ally picks/bans, enemy picks/bans
  * output: ranked recommendations + explanation objects
* `GET /v1/meta/patches` (so UI can switch patches)
* `GET /health`

**Frontend**

* Draft board (5 roles each side)
* Ban slots (optional but nice)
* Results table: champ, score, “why”, counters, synergy
* “Lock candidate” button (lets user simulate next pick)

**Evaluation (real numbers in README)**

* Offline: on held-out drafts

  * **Top-K recall**: “did the true picked champ appear in top 10?”
  * **NDCG@K**: ranking quality
  * Calibration sanity check: higher score correlates with higher winrate

### Solves after M1 (demo scenarios)

✅ “Given these picks, what should I pick next (top 10) and why?”
✅ “Show me counters and synergies transparently (not a black box).”
✅ “Patch-aware draft guidance.”

**Resume bullet you can honestly write**

* “Built an end-to-end ML draft recommendation system for LoL: rate-limited data ingestion → Bayesian-smoothed synergy/counter models → FastAPI inference → React UI, achieving NDCG@10 = X on held-out drafts.”

---

## M2 — Win Probability Model (supervised learning upgrade)

**Goal:** Replace heuristic scoring with a learned **win-prob predictor** and use it for ranking.

**Deliverables**

* Train a model (start with LightGBM/logistic regression):

  * features: champ IDs per role, pair interactions (hashed), patch, rank bucket
  * target: win/loss
* Draft recommendation becomes:

  * For each candidate champ: compute **Δ win prob** vs baseline pick
* Add **calibration** (Platt/isotonic) + reliability plot

**Solves after M2**
✅ “This pick increases predicted win chance by +3.2% (calibrated).”
✅ Better generalization than raw matchup tables.

---

## M3 — Draft Planning (game theory-ish search)

**Goal:** Turn “recommend next pick” into “recommend a **plan**”.

**Deliverables**

* A draft simulator:

  * you pick → opponent responds → you respond…
* Opponent model options:

  * greedy best-response using your win-prob model
  * or “mixture” (best-response + meta pickrate)
* Search method:

  * beam search or lightweight MCTS
* Output:

  * top 3 candidate picks + expected value **after** simulated responses
  * “if they pick X, your best answer is Y”

**Solves after M3**
✅ Feels like real decision-making under adversaries (game theory flavor)
✅ Great interview story: “model + search = policy”.

---

## M4 — Item Path Optimizer (sequence modeling + Markov/MDP framing)

**Goal:** Move beyond “most common build” into **contextual item sequences**.

**M4.1 (shippable baseline)**

* From match timelines, learn:

  * next-item probabilities conditioned on champ+role+enemy comp archetype
* Recommend:

  * starter + core 3 items
  * “next item” suggestions (Markov chain / n-gram style)

**M4.2 (stronger, more MLE)**

* Train a model to predict next purchase (classification)
* Add constraints:

  * gold/time windows
  * mutually exclusive items
* Output explanations:

  * “anti-heal needed”, “armor stack”, “burst threat”

---

## M5 — Personalization with Contextual Bandits

**Goal:** Monetizable “coach” feel: adapts to *you*.

**Deliverables**

* User profile: champ pool, role preference, style embedding
* A contextual bandit layer that trades off:

  * win-prob gain
  * user comfort/mastery
  * diversity/learning
* Offline evaluation (OPE):

  * IPS / doubly-robust estimates (even if simplified)

**Solves after M5**
✅ “Best pick for *you*, not just the meta.”
✅ Clear monetization hook (premium personalization).

---

## M6 — Productization + Monetization (policy-safe)

**Goal:** Make it a real product you *could* charge for without getting nuked.

**Deliverables**

* Account system + subscription gating (still with a free tier) ([developer.riotgames.com][1])
* Payments (Stripe)
* Feature tiers (example)

  * Free: draft recs + basic explanations
  * Pro: draft planning (M3), personalization (M5), deeper analytics
* Strict compliance:

  * **No ads inside game / loading / Riot client** ([developer.riotgames.com][1])
* Production key readiness + caching strategy + backoff behavior ([developer.riotgames.com][2])

---

# “AI Engineer polish” checklist (what makes recruiters instantly get it)

Include these pages in your README / docs:

* **System diagram** (ingestion → training → registry → inference → UI)
* **Offline evaluation report** (NDCG@K, calibration, slice metrics by rank/patch)
* **Data versioning** (patch partitioning; reproducible training runs)
* **Latency** (p50/p95 for recommend endpoint; caching wins)
* **Guardrails** (don’t recommend banned champs; role constraints; explainability)

---

## If you want the absolute highest-likelihood MVP

Do M1 with:

* Draft only (no items yet)
* Explanations + offline metrics
* Clean UI and a short demo video

Then M2 (win-prob model) is your “wow, real ML” upgrade.

If you want, I can also write the **full README skeleton + repo structure** (folders, scripts, endpoints, and exactly what to implement in each file) for M1 so you can start coding immediately.

[1]: https://developer.riotgames.com/policies/general "Riot Developer Portal"
[2]: https://developer.riotgames.com/docs/portal "Riot Developer Portal"