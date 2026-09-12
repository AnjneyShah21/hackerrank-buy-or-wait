# Buy or Wait? — Evaluation Report

## Summary

- **Sample requests evaluated:** 25
- **Overall exact-match rate:** 12.0%
- **Runtime:** 2.65s
- **Estimated cost:** $0.0000

## Field-Level Accuracy

| Field | Accuracy |
|:---|---:|
| affordability_status | 76.0% |
| recommended_payment_method | 84.0% |
| amount_safe_to_pay (±1%) | 12.0% |
| payment_plan | 76.0% |
| earliest_date_for_full_payment | 64.0% |
| spending_changes_needed | 84.0% |

## Per-Request Comparison

| request_id | Overall | status | method | amount | date | plan | spending |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| request_01 | OK | OK | OK | OK | OK | OK | OK |
| request_02 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_03 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_04 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_05 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_06 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_07 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_08 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_09 | OK | OK | OK | OK | OK | OK | OK |
| request_10 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_11 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_12 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_13 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| request_14 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_15 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_16 | OK | OK | OK | OK | OK | OK | OK |
| request_17 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_18 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_19 | FAIL | OK | FAIL | FAIL | FAIL | FAIL | OK |
| request_20 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_21 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_22 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_23 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_24 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_25 | FAIL | OK | OK | FAIL | OK | OK | OK |

## Failure Details

### request_02

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `15952906.67` | `17229139.2` |

### request_03

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `835019.9` | `873000` |
| earliest_date_for_full_payment | `2019-11-30` | `2019-11-15` |
| payment_plan | `2019-11-30:5491000` | `2019-11-15:5491000` |

### request_04

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_later` |
| recommended_payment_method | `full_payment` | `wait` |
| amount_safe_to_pay | `12693000` | `8401800` |
| earliest_date_for_full_payment | `2024-06-04` | `2024-06-15` |
| payment_plan | `2024-06-04:12693000` | `2024-06-15:12693000` |

### request_05

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `1505.3` | `737` |

### request_06

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_with_plan` |
| amount_safe_to_pay | `620.4` | `603.3` |
| earliest_date_for_full_payment | `2026-01-03` | `2026-01-15` |
| spending_changes_needed | `none` | `stop:event_476` |

### request_07

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `68432` | `87170.56` |

### request_08

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_later` |
| recommended_payment_method | `not_recommended` | `wait` |
| amount_safe_to_pay | `425.04` | `284.57` |
| earliest_date_for_full_payment | `` | `2025-04-15` |
| payment_plan | `none` | `2025-04-15:996.60` |

### request_10

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `23594.22` | `12700` |

### request_11

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_with_plan` |
| amount_safe_to_pay | `13110000` | `12510645` |
| earliest_date_for_full_payment | `2025-05-03` | `2025-07-15` |
| spending_changes_needed | `none` | `reduce_to:event_989:665950` |

### request_12

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `22590.19` | `65164` |

### request_13

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `affordable_later` |
| recommended_payment_method | `full_payment` | `wait` |
| amount_safe_to_pay | `929.83` | `433.4` |
| earliest_date_for_full_payment | `` | `2024-05-15` |
| payment_plan | `2024-03-07:941.60` | `2024-05-15:941.60` |
| spending_changes_needed | `stop:event_1091|stop:event_1090|reduce_to:event_1092:30.50` | `none` |

### request_14

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `1058.19` | `597.74` |

### request_15

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `108.01` | `83.05` |

### request_17

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `95194.67` | `243849.58` |

### request_18

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `812.73` | `462` |
| earliest_date_for_full_payment | `2026-08-15` | `2026-09-15` |
| payment_plan | `2026-08-15:3246.10` | `2026-09-15:3246.10` |

### request_19

| Field | Predicted | Expected |
|:---|:---|:---|
| recommended_payment_method | `installments` | `partial_payment` |
| amount_safe_to_pay | `20623.2` | `28820` |
| earliest_date_for_full_payment | `2024-09-04` | `2024-09-15` |
| payment_plan | `2024-09-04:20623.20|2024-10-02:20623.20` | `2024-09-04:28820|2024-09-15:10840` |

### request_20

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `26194.8` | `5400` |

### request_21

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_with_plan` |
| amount_safe_to_pay | `1574.4` | `1543.35` |
| earliest_date_for_full_payment | `2026-04-03` | `2026-04-15` |
| spending_changes_needed | `none` | `stop:event_1815|reduce_to:event_1816:23.50` |

### request_22

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `253.59` | `475.46` |

### request_23

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `12844.17` | `9152` |

### request_24

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `19651.09` | `13420` |

### request_25

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `5287713.95` | `1425000` |

## Failure Categories

| Category | Count | Request IDs |
|:---|:---:|:---|
| wrong_amount_safe | 22 | request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25 |
| wrong_earliest_date | 9 | request_03, request_04, request_06, request_08, request_11, request_13, request_18, request_19, request_21 |
| wrong_affordability_status | 6 | request_04, request_06, request_08, request_11, request_13, request_21 |
| wrong_plan_dates | 5 | request_03, request_04, request_08, request_13, request_18 |
| wrong_payment_method | 4 | request_04, request_08, request_13, request_19 |
| wrong_spending_changes | 4 | request_06, request_11, request_13, request_21 |
| wrong_plan_amounts | 1 | request_19 |

## Systematic Patterns

- wrong_amount_safe: 22 request(s) — request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25
- wrong_earliest_date: 9 request(s) — request_03, request_04, request_06, request_08, request_11, request_13, request_18, request_19, request_21
- wrong_affordability_status: 6 request(s) — request_04, request_06, request_08, request_11, request_13, request_21
- wrong_plan_dates: 5 request(s) — request_03, request_04, request_08, request_13, request_18
- wrong_payment_method: 4 request(s) — request_04, request_08, request_13, request_19
- wrong_spending_changes: 4 request(s) — request_06, request_11, request_13, request_21
- wrong_plan_amounts: 1 request(s) — request_19

## Usage & Telemetry

| Metric | Value |
|:---|:---|
| Total requests | 25 |
| Image extraction calls | 16 |
| Image facts extracted | 16 |
| Message interpretation calls | 215 |
| Message facts extracted | 95 |
| LLM/API calls | 0 |
| Input tokens | 0 |
| Output tokens | 0 |
| Total tokens | 0 |
| Retries | 0 |
| Cache hits | 0 |
| Estimated cost (USD) | $0.0000 |
| Runtime (s) | 2.65 |

