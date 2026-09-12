# Buy or Wait? — Evaluation Report

## Summary

- **Sample requests evaluated:** 25
- **Overall exact-match rate:** 8.0%
- **Runtime:** 1.55s
- **Estimated cost:** $0.0000

## Field-Level Accuracy

| Field | Accuracy |
|:---|---:|
| affordability_status | 68.0% |
| recommended_payment_method | 80.0% |
| amount_safe_to_pay (±1%) | 12.0% |
| payment_plan | 68.0% |
| earliest_date_for_full_payment | 48.0% |
| spending_changes_needed | 88.0% |

## Per-Request Comparison

| request_id | Overall | status | method | amount | date | plan | spending |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| request_01 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_02 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_03 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_04 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_05 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_06 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_07 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_08 | FAIL | FAIL | FAIL | OK | FAIL | FAIL | OK |
| request_09 | OK | OK | OK | OK | OK | OK | OK |
| request_10 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_11 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_12 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_13 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_14 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_15 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_16 | OK | OK | OK | OK | OK | OK | OK |
| request_17 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_18 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_19 | FAIL | OK | OK | FAIL | OK | FAIL | OK |
| request_20 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_21 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_22 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_23 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_24 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_25 | FAIL | OK | OK | FAIL | OK | OK | OK |

## Failure Details

### request_01

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_now` |
| recommended_payment_method | `not_recommended` | `full_payment` |
| amount_safe_to_pay | `21537.32` | `25256` |
| earliest_date_for_full_payment | `` | `2024-03-03` |
| payment_plan | `none` | `2024-03-03:25256` |

### request_02

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `installments` |
| amount_safe_to_pay | `18081586.73` | `17229139.2` |
| earliest_date_for_full_payment | `2025-10-15` | `2025-09-15` |
| payment_plan | `none` | `2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67` |

### request_03

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `1297461.89` | `873000` |
| earliest_date_for_full_payment | `2019-10-15` | `2019-11-15` |
| payment_plan | `2019-10-15:5491000` | `2019-11-15:5491000` |

### request_04

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `12079514.66` | `8401800` |

### request_05

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `6092.83` | `737` |

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
| amount_safe_to_pay | `68432.0` | `87170.56` |
| earliest_date_for_full_payment | `2024-11-15` | `2024-10-23` |

### request_08

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_later` |
| recommended_payment_method | `not_recommended` | `wait` |
| earliest_date_for_full_payment | `` | `2025-04-15` |
| payment_plan | `none` | `2025-04-15:996.60` |

### request_10

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `266700.0` | `12700` |
| earliest_date_for_full_payment | `2024-12-06` | `` |

### request_11

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_with_plan` |
| amount_safe_to_pay | `13110000.0` | `12510645` |
| earliest_date_for_full_payment | `2025-05-03` | `2025-07-15` |
| spending_changes_needed | `none` | `reduce_to:event_989:665950` |

### request_12

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `22590.19` | `65164` |

### request_13

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `affordable_later` |
| recommended_payment_method | `full_payment` | `wait` |
| amount_safe_to_pay | `941.6` | `433.4` |
| earliest_date_for_full_payment | `2024-03-07` | `2024-05-15` |
| payment_plan | `2024-03-07:941.60` | `2024-05-15:941.60` |

### request_14

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `not_affordable` |
| recommended_payment_method | `partial_payment` | `not_recommended` |
| amount_safe_to_pay | `693.85` | `597.74` |
| earliest_date_for_full_payment | `2025-09-15` | `` |
| payment_plan | `2025-08-04:693.85|2025-09-15:4720.35` | `none` |

### request_15

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `167.88` | `83.05` |

### request_17

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `95194.67` | `243849.58` |

### request_18

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `591.53` | `462` |
| earliest_date_for_full_payment | `2026-08-15` | `2026-09-15` |
| payment_plan | `2026-08-15:3246.10` | `2026-09-15:3246.10` |

### request_19

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `33738.8` | `28820` |
| payment_plan | `2024-09-04:33738.80|2024-09-15:5921.20` | `2024-09-04:28820|2024-09-15:10840` |

### request_20

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `17493.15` | `5400` |

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
| earliest_date_for_full_payment | `2024-12-15` | `2025-01-15` |

### request_23

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `13215.1` | `9152` |

### request_24

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `20568.24` | `13420` |

### request_25

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `2693072.22` | `1425000` |

## Failure Categories

| Category | Count | Request IDs |
|:---|:---:|:---|
| wrong_amount_safe | 22 | request_01, request_02, request_03, request_04, request_05, request_06, request_07, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25 |
| wrong_earliest_date | 13 | request_01, request_02, request_03, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_18, request_21, request_22 |
| wrong_affordability_status | 8 | request_01, request_02, request_06, request_08, request_11, request_13, request_14, request_21 |
| wrong_payment_method | 5 | request_01, request_02, request_08, request_13, request_14 |
| wrong_plan_dates | 5 | request_01, request_03, request_08, request_13, request_18 |
| wrong_spending_changes | 3 | request_06, request_11, request_21 |
| wrong_plan_entry_count | 2 | request_02, request_14 |
| wrong_plan_amounts | 1 | request_19 |

## Systematic Patterns

- wrong_amount_safe: 22 request(s) — request_01, request_02, request_03, request_04, request_05, request_06, request_07, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25
- wrong_earliest_date: 13 request(s) — request_01, request_02, request_03, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_18, request_21, request_22
- wrong_affordability_status: 8 request(s) — request_01, request_02, request_06, request_08, request_11, request_13, request_14, request_21
- wrong_payment_method: 5 request(s) — request_01, request_02, request_08, request_13, request_14
- wrong_plan_dates: 5 request(s) — request_01, request_03, request_08, request_13, request_18
- wrong_spending_changes: 3 request(s) — request_06, request_11, request_21
- wrong_plan_entry_count: 2 request(s) — request_02, request_14
- wrong_plan_amounts: 1 request(s) — request_19

## Usage & Telemetry

| Metric | Value |
|:---|:---|
| Total requests | 25 |
| Image extraction calls | 16 |
| Image facts extracted | 16 |
| Message interpretation calls | 215 |
| Message facts extracted | 90 |
| LLM/API calls | 0 |
| Input tokens | 0 |
| Output tokens | 0 |
| Total tokens | 0 |
| Retries | 0 |
| Cache hits | 0 |
| Estimated cost (USD) | $0.0000 |
| Runtime (s) | 1.55 |

