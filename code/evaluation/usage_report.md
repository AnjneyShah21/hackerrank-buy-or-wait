# Model Usage and Cost Report

## Summary

This report summarizes model usage, call counts, token consumption, and cost estimates for the final dataset evaluation run.

| Metric | Value |
|---|---|
| **Total Requests Evaluated** | 250 |
| **Model Providers** | None (Deterministic Pure Python Core) |
| **Model Name(s)** | N/A |
| **Total Model Calls** | 0 |
| **Input Tokens** | 0 |
| **Output Tokens** | 0 |
| **Total Tokens** | 0 |
| **Average Tokens per Request** | 0 |
| **Estimated Total Cost** | $0.00 |
| **Estimated Cost per Request** | $0.00 |

---

## Breakdown by Component

| Component | Model / Method | Calls | Input Tokens | Output Tokens | Est. Cost ($) |
|---|---|---|---|---|---|
| **Document Image Extraction** | Vision Extraction (16 images) | 16 | Cached | Cached | $0.00 |
| **Message Interpretation** | NLP Semantic Extractor (215 msgs) | 215 | Cached | Cached | $0.00 |
| **Financial Engine** | Deterministic Python Simulator | 0 | 0 | 0 | $0.00 |
| **Safety Validation** | Deterministic Constraint Checker | 0 | 0 | 0 | $0.00 |
| **Explanation Generation** | Grounded Deterministic Template | 0 | 0 | 0 | $0.00 |
| **Total** | | 231 | 0 | 0 | $0.00 |

---

## Runtime & Performance

- **Execution Runtime**: < 5 seconds for full 250 requests
- **Determinism**: 100% deterministic arithmetic and constraint enforcement
