# Buy or Wait? — Evaluation Report

## Summary

- **Sample requests evaluated:** 25
- **Overall exact-match rate:** 8.0%
- **Runtime:** 3.16s
- **Estimated cost:** $0.0000

## Field-Level Accuracy

| Field | Accuracy |
|:---|---:|
| affordability_status | 52.0% |
| recommended_payment_method | 64.0% |
| amount_safe_to_pay (±1%) | 8.0% |
| payment_plan | 56.0% |
| earliest_date_for_full_payment | 36.0% |
| spending_changes_needed | 84.0% |

## Per-Request Comparison

| request_id | Overall | status | method | amount | date | plan | spending |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| request_01 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_02 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_03 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_04 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_05 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_06 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| request_07 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_08 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_09 | OK | OK | OK | OK | OK | OK | OK |
| request_10 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_11 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_12 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_13 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_14 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_15 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_16 | OK | OK | OK | OK | OK | OK | OK |
| request_17 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_18 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_19 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_20 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_21 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_22 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_23 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_24 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_25 | FAIL | OK | OK | FAIL | OK | OK | OK |

## Failure Details

### request_01

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `affordable_now` |
| amount_safe_to_pay | `24477.0` | `25256` |
| earliest_date_for_full_payment | `` | `2024-03-03` |
| spending_changes_needed | `stop:event_31` | `none` |

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
| amount_safe_to_pay | `819403.78` | `873000` |
| earliest_date_for_full_payment | `2019-09-20` | `2019-11-15` |
| payment_plan | `2019-09-20:5491000` | `2019-11-15:5491000` |

### request_04

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `7384544.0` | `8401800` |

### request_05

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_now` | `not_affordable` |
| recommended_payment_method | `full_payment` | `not_recommended` |
| amount_safe_to_pay | `15488.0` | `737` |
| earliest_date_for_full_payment | `2025-11-06` | `` |
| payment_plan | `2025-11-06:15488` | `none` |

### request_06

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `full_payment` |
| amount_safe_to_pay | `490.0` | `603.3` |
| earliest_date_for_full_payment | `` | `2026-01-15` |
| payment_plan | `none` | `2026-01-03:620.40` |
| spending_changes_needed | `none` | `stop:event_476` |

### request_07

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `68432.0` | `87170.56` |
| earliest_date_for_full_payment | `2024-10-24` | `2024-10-23` |

### request_08

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_later` |
| recommended_payment_method | `not_recommended` | `wait` |
| amount_safe_to_pay | `234.0` | `284.57` |
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
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `installments` |
| amount_safe_to_pay | `62374.97` | `65164` |
| earliest_date_for_full_payment | `` | `2026-04-05` |
| payment_plan | `none` | `2026-04-19:22590.19|2026-05-20:22590.19|2026-06-20:22590.19` |

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
| amount_safe_to_pay | `403.0` | `597.74` |
| earliest_date_for_full_payment | `2025-09-15` | `` |
| payment_plan | `2025-08-04:403|2025-09-15:5011.20` | `none` |

### request_15

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `9.0` | `83.05` |

### request_17

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `installments` |
| amount_safe_to_pay | `150316.0` | `243849.58` |
| earliest_date_for_full_payment | `` | `2026-03-15` |
| payment_plan | `none` | `2026-03-01:95194.67|2026-03-31:95194.67|2026-04-30:95194.67` |

### request_18

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `591.53` | `462` |
| earliest_date_for_full_payment | `2026-08-15` | `2026-09-15` |
| payment_plan | `2026-08-15:3246.10` | `2026-09-15:3246.10` |

### request_19

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `partial_payment` |
| amount_safe_to_pay | `27130.0` | `28820` |
| earliest_date_for_full_payment | `2024-11-15` | `2024-09-15` |
| payment_plan | `none` | `2024-09-04:28820|2024-09-15:10840` |

### request_20

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `9022.73` | `5400` |

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
| amount_safe_to_pay | `11899.0` | `9152` |

### request_24

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `14276.93` | `13420` |

### request_25

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `0.0` | `1425000` |

## Failure Categories

| Category | Count | Request IDs |
|:---|:---:|:---|
| wrong_amount_safe | 23 | request_01, request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25 |
| wrong_earliest_date | 16 | request_01, request_02, request_03, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_17, request_18, request_19, request_21 |
| wrong_affordability_status | 12 | request_01, request_02, request_05, request_06, request_08, request_11, request_12, request_13, request_14, request_17, request_19, request_21 |
| wrong_payment_method | 9 | request_02, request_05, request_06, request_08, request_12, request_13, request_14, request_17, request_19 |
| wrong_plan_dates | 6 | request_03, request_05, request_06, request_08, request_13, request_18 |
| wrong_plan_entry_count | 5 | request_02, request_12, request_14, request_17, request_19 |
| wrong_spending_changes | 4 | request_01, request_06, request_11, request_21 |

## Systematic Patterns

- wrong_amount_safe: 23 request(s) — request_01, request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25
- wrong_earliest_date: 16 request(s) — request_01, request_02, request_03, request_05, request_06, request_07, request_08, request_10, request_11, request_12, request_13, request_14, request_17, request_18, request_19, request_21
- wrong_affordability_status: 12 request(s) — request_01, request_02, request_05, request_06, request_08, request_11, request_12, request_13, request_14, request_17, request_19, request_21
- wrong_payment_method: 9 request(s) — request_02, request_05, request_06, request_08, request_12, request_13, request_14, request_17, request_19
- wrong_plan_dates: 6 request(s) — request_03, request_05, request_06, request_08, request_13, request_18
- wrong_plan_entry_count: 5 request(s) — request_02, request_12, request_14, request_17, request_19
- wrong_spending_changes: 4 request(s) — request_01, request_06, request_11, request_21

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
| Runtime (s) | 3.16 |

