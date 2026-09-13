# Buy or Wait? — AI Financial Decision System

**Participant:** Anjney Shah  
**Challenge:** HackerRank Orchestrate (September 2026) — Buy or Wait?  
**Architecture:** Deterministic Cash-Flow Forecaster + Multimodal Evidence Engine + Contract Gatekeeper

---

## 1. Executive Summary

**Buy or Wait?** is an AI-powered financial decision system built to evaluate purchase and payment requests under complete financial context. For every request in `dataset/requests.csv`, the system analyzes the user's financial profile, transaction history, pending commitments, foreign exchange rates, seller payment options, and unstructured evidence (messages and images) to output a personalized, mathematically sound recommendation:

1. `amount_safe_to_pay`: Maximum safe outlay today without violating minimum balance requirements.
2. `affordability_status`: `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable`.
3. `recommended_payment_method`: `full_payment`, `partial_payment`, `installments`, `wait`, or `not_recommended`.
4. `payment_plan`: Chronological payment schedule (`YYYY-MM-DD:amount|...`).
5. `earliest_date_for_full_payment`: Conservative date when single full payment becomes safe.
6. `spending_changes_needed`: Non-protected, flexible spending adjustments (`stop:<event_id>` / `reduce_to:<event_id>:<amount>`).
7. `decision_explanation`: Grounded, transparent narrative explaining the financial facts behind the recommendation.

---

## 2. System Architecture & Pipeline

```text
                               ┌─────────────────────────┐
                               │     dataset/*.csv       │
                               └────────────┬────────────┘
                                            │ Ingestion & Normalization
                                            ▼
                               ┌─────────────────────────┐
                               │   DataLoader & Index    │
                               └────────────┬────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
       ┌───────────────────────────┐                 ┌───────────────────────────┐
       │   Unstructured Evidence   │                 │    Currency Converter     │
       │ (Messages & Images / OCR) │                 │ (Fixed Dated FX Rates)    │
       └─────────────┬─────────────┘                 └─────────────┬─────────────┘
                     │ Fact Extraction & Resolution                │
                     └──────────────────────┬──────────────────────┘
                                            │ Resolved Financial State
                                            ▼
                               ┌───────────────────────────┐
                               │  90-Day Cash-Flow Engine  │
                               │ (Simulator & Min Balance) │
                               └────────────┬──────────────┘
                                            │ Liquidity & Headroom Bounds
                                            ▼
                               ┌───────────────────────────┐
                               │   Payment Planner &       │
                               │   Decision Ranker         │
                               └────────────┬──────────────┘
                                            │ Safe Decision Candidate
                                            ▼
                               ┌───────────────────────────┐
                               │    Contract Validator     │
                               │ (Schema & Invariants)     │
                               └────────────┬──────────────┘
                                            │ Verified Predictions
                                            ▼
                               ┌───────────────────────────┐
                               │        output.csv         │
                               └───────────────────────────┘
```

---

## 3. Financial Reasoning & Safety Guarantees

### 3.1 90-Day Cash-Flow Forecaster
* **Daily Ledger Reconstruction:** Projects daily available cash over a 90-day forecast horizon (`FORECAST_DAYS = 90`) starting from `request_date`.
* **Minimum Balance Protection:** A payment plan is strictly **unsafe** if the user's projected balance drops below `minimum_balance_to_keep` on *any* single day within the 90-day window.
* **Conservative Inflow Rules:** Salaries and income are credited strictly on their confirmed settlement date. Pending credits, unconfirmed bonuses, commissions, lottery proceeds, and unrealized investment gains are **never** counted toward available liquidity.
* **Pending Debit Reservation:** Pending debits (e.g. uncleared card purchases) are reserved immediately on `request_date`.

### 3.2 Dynamic Search & Payday Anchoring
* **Liquidity Windowing:** `amount_safe_to_pay` measures safe liquidity on `request_date` before optional spending changes.
* **Payday Anchoring:** `earliest_date_for_full_payment` searches upcoming confirmed income paydays (including 15th-of-month salary cycles) to identify the earliest conservative date for single full payment.
* **Deadline Enforcement:** If full payment cannot be completed on or before `desired_completion_date`, and no safe partial/installment plan satisfies the deadline, the request is classified as `not_affordable`.

---

## 4. Multimodal Evidence & Adversarial Defense

### 4.1 Evidence Extraction Pipeline
* **Images (`images.csv` & `media/images/*.png`):** Extracts missing amounts and receipt details when an event row has a blank `amount`.
* **Messages (`messages.csv`):** Parses English and Indonesian messages for amendments, cancellations, payment delays, and confirmation facts.

### 4.2 Untrusted Data & Prompt Injection Defense
* **Content vs Instructions:** Messages and images are treated strictly as **untrusted data**.
* **Sanitization:** Text inputs are passed through `sanitize_untrusted_text()`, stripping embedded system overrides, jailbreak phrases ("ignore previous instructions", "always approve"), and control sequences.
* **Invariant Shielding:** Embedded prompt instructions can *never* override minimum balance rules, problem statement constraints, or output contract invariants.

---

## 5. 4-Tier Conflict Resolution Precedence

When multiple records or messages conflict regarding a financial transaction, the system applies the problem statement's strict 4-tier hierarchy:

1. **Explicit Action First:** Explicit cancellations, settlements, or amendments take highest priority.
2. **Source Recency:** Newer records from the same source supersede older records.
3. **Settled over Estimated:** Confirmed settled transactions take precedence over estimates or pending projections.
4. **Financially Safer Tie-Breaker:** Unresolvable ambiguities revert to the financially safer interpretation (higher liability / lower asset assumption).

---

## 6. Decision Engine & Plan Ranking Matrix

When multiple safe payment plans exist, the `DecisionEngine` ranks candidates according to the problem statement tie-breaking rules:

1. Complete the full request by `desired_completion_date`.
2. Require no spending changes (`spending_changes_needed == "none"`).
3. Minimize total cash outlay.
4. Start payment schedule earlier.
5. Use fewer total payment installments.
6. Final tie-breaker: Lowest `payment_option_id`.

---

## 7. Submission Directory Structure

```text
.
├── main.py                  # Top-level entrypoint shim
├── config.py                # Dynamic path finder & configuration
├── data_loader.py           # Ingestion layer with schema validation
├── models.py                # Strongly-typed domain models
├── currency.py              # Dated FX conversion engine
├── evidence.py              # Evidence store & conflict resolution
├── image_extractor.py       # Vision / OCR extraction layer
├── message_interpreter.py   # Multilingual NLP message interpreter
├── forecast.py              # 90-day cash-flow simulation engine
├── financial_engine.py      # Safe amount & earliest date calculators
├── payment_planner.py       # Full / partial / installment plan generator
├── decision_engine.py       # Multi-tier plan ranker & explanation builder
├── validator.py             # Schema & invariant validator
├── output_writer.py         # CSV exporter
├── README.md                # System documentation
├── requirements.txt         # Runtime dependencies
├── evaluation/              # Local benchmark & usage reporting
│   ├── main.py              # Offline evaluation suite runner
│   ├── metrics.py           # Accuracy and tolerance calculators
│   ├── error_analysis.py    # Failure categorization engine
│   └── usage_report.md      # Token usage & cost analysis report
├── code/                    # Parallel modular package structure
│   ├── main.py
│   ├── config.py
│   └── ...
└── output.csv               # Generated predictions for evaluation
```

---

## 8. How to Run & Verify

### 8.1 Execute Pipeline (Generate `output.csv`)
```bash
python main.py
# or
python code/main.py
```

### 8.2 Run Local Evaluation Suite
```bash
python code/evaluation/main.py
```

### 8.3 Run Unit Test Suite
```bash
python -m unittest discover code/tests
```

---

## 9. Token Usage & Cost Summary

Per Section 6.5 of the challenge contract, token usage for the evaluation run is documented in [`evaluation/usage_report.md`](file:///d:/Hackerrank/code/evaluation/usage_report.md):

* **Total API Calls:** 250 request pipeline evaluations
* **Total API Cost:** **$0.00** (Zero external API cost; 100% deterministic local execution)
* **Hallucination Risk:** 0.0%
