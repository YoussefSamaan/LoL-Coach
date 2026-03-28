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
