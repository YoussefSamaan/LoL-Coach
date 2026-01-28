# Machine Learning Model & Scoring Engine

This directory contains the logic for the **Additive Lift Model**, which powers the champion recommendations in LoL Coach.

## Goal
The goal is to estimate the probability that a specific champion, played in a specific role, will win the game given the current partial draft (allies and enemies).

$$ P(\text{Win} | \text{Draft}) $$

## Methodology: Additive Lift Model
We chose an interpretable **Additive Lift Model** over valid black-box approaches (like Deep Neural Networks) or pure Naive Bayes. This allows us to explain *exactly* why a champion is recommended (e.g., "Synergy with Amumu: +3.2%").

### 1. Training (Offline Aggregation)
The `build_tables.py` script aggregates historical match data to compute three key components. We use **Bayesian Smoothing** (Beta priors) to handle low-sample-size data effectively.

#### A. Base Role Strength
The baseline winrate of a champion in a specific role (e.g., Ahri MID).
$$ P_{\text{base}} = \frac{\text{wins} + \alpha}{\text{games} + \alpha + \beta} $$

#### B. Synergy Lift
How much a champion's winrate *changes* when played with a specific ally.
$$ \text{Lift}_{\text{synergy}}(C, A) = P(C \text{ wins} | A \text{ is ally}) - P(C \text{ wins}) $$

#### C. Counter Lift
How much a champion's winrate *changes* when played against a specific enemy.
$$ \text{Lift}_{\text{counter}}(C, E) = P(C \text{ wins} | E \text{ is enemy}) - P(C \text{ wins}) $$

> **Note**: These lifts are clamped and smoothed to prevent noisy outliers (e.g., 100% winrate from 1 game) from dominating recommendations.

---

### 2. Inference (Real-time Scoring)
The `scoring/inference.py` module calculates the final score at runtime. To ensure mathematical stability and proper probability bounding [0, 1], we operate in **Logit Space** (Log-Odds).

#### The Formula
$$ \text{Logit}_{\text{final}} = \text{Logit}(P_{\text{base}}) + \text{Scale} \times \left( \sum w_s \cdot \text{Lift}_{\text{synergy}} + \sum w_c \cdot \text{Lift}_{\text{counter}} \right) $$

Where:
- $\text{Logit}(p) = \ln(\frac{p}{1-p})$
- **Scale**: A constant (default ~4.0) that maps raw probability deltas to logit differences (approx. 1% winrate $\approx$ 0.04 logit).
- $w_s, w_c$: Configurable weights for synergy and counter importance.

#### Final Probability
The final score is converted back to a probability using the sigmoid function:
$$ P_{\text{final}} = \frac{1}{1 + e^{-\text{Logit}_{\text{final}}}} $$

### Why Logit Space?
Simply adding probabilities (e.g., $50\% + 10\% + 50\% = 110\%$) can lead to impossible results (>100% or <0%). Logit space naturally handles these bounds, ensuring that diminishing returns apply as probabilities approach 0 or 1.
