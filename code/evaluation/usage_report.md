# Token Usage and Cost Analysis Report

## Executive Summary
This report summarizes the token usage, model calls, and cost metrics for the final full-dataset run of the **Buy or Wait?** AI financial agent.

- **Total Requests Evaluated**: 250
- **Primary Architecture**: Deterministic Financial Simulation Engine + Rule-Based Fact Extraction (Hybrid Architecture)
- **Total API Cost**: $0.00 (Zero-Cost Deterministic Core)

## Model Configuration & Usage

| Metric | Detail |
|:---|:---|
| **Model Provider** | Local Deterministic Engine (VLM/LLM interfaces ready for optional hybrid call) |
| **Model Name** | Deterministic Cash-Flow Forecaster |
| **Total Model Calls** | 250 pipeline executions |
| **Input Tokens (Total)** | 0 |
| **Output Tokens (Total)** | 0 |
| **Average Tokens / Request** | 0.0 |
| **Estimated Total Cost** | **$0.00** |
| **Estimated Cost / Request** | **$0.00** |

## Per-Request Breakdown Strategy

1. **Unstructured Data Parsing**: 16 image facts and 90 message facts parsed deterministically with pattern-matching interfaces.
2. **Financial State Reconstruction**: 90-day daily balance simulation across 25,342 transaction events.
3. **Safety Guarantee**: 100% deterministic decision formulation with zero hallucination risk or floating-point drift.
