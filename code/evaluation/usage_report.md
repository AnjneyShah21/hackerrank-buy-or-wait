# Token Usage and Cost Analysis Report

## Executive Summary

- **Total Requests Evaluated (full dataset):** 250
- **Architecture:** Deterministic Cash-Flow Simulation Engine + Rule-Based Fact Extraction
- **Total API Cost:** $0.00 (zero-cost deterministic core)

## Model Configuration & Usage

| Metric | Detail |
|:---|:---|
| Model Provider | Deterministic Engine (no external API calls) |
| Model Name | Buy or Wait? Deterministic Cash-Flow Forecaster |
| Total Model Calls | 250 pipeline executions |
| Input Tokens (Total) | 0 |
| Output Tokens (Total) | 0 |
| Average Tokens / Request | 0.0 |
| Estimated Total Cost | **$0.00** |
| Estimated Cost / Request | **$0.00** |

## Image & Message Extraction

| Metric | Value |
|:---|:---|
| Image extraction calls | 16 |
| Image facts extracted | 16 |
| Message interpretation calls | 215 |
| Message facts extracted | 95 |
| Retries | 0 |
| Cache hits | 0 |

## Runtime

- **Sample evaluation runtime:** 2.08s
- **Forecast horizon:** 90 days per request

## Per-Request Summary

1. **Evidence Parsing:** 16 image facts + 95 message facts parsed deterministically.
2. **Financial State:** 90-day daily balance simulation with event deduplication, recurrence detection, and foreign currency conversion.
3. **Safety Guarantee:** 100% deterministic decision logic — zero hallucination risk.
