# Buy or Wait? — Evaluation Report

## Summary

- **Sample requests evaluated:** 25
- **Overall exact-match rate:** 4.0%
- **Runtime:** 5.0s
- **Estimated cost:** $0.0000

## Field-Level Accuracy

| Field | Accuracy |
|:---|---:|
| affordability_status | 52.0% |
| recommended_payment_method | 60.0% |
| amount_safe_to_pay (±1%) | 16.0% |
| payment_plan | 56.0% |
| earliest_date_for_full_payment | 44.0% |
| spending_changes_needed | 88.0% |

## Per-Request Comparison

| request_id | Overall | status | method | amount | date | plan | spending |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| request_01 | OK | OK | OK | OK | OK | OK | OK |
| request_02 | FAIL | FAIL | FAIL | FAIL | OK | FAIL | OK |
| request_03 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_04 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_05 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_06 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_07 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_08 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_09 | FAIL | FAIL | FAIL | OK | OK | OK | OK |
| request_10 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_11 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_12 | FAIL | OK | OK | OK | OK | FAIL | OK |
| request_13 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_14 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_15 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_16 | FAIL | FAIL | FAIL | OK | OK | OK | OK |
| request_17 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | OK |
| request_18 | FAIL | OK | OK | FAIL | FAIL | FAIL | OK |
| request_19 | FAIL | OK | FAIL | FAIL | FAIL | FAIL | OK |
| request_20 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_21 | FAIL | FAIL | OK | FAIL | FAIL | OK | FAIL |
| request_22 | FAIL | OK | OK | FAIL | FAIL | OK | OK |
| request_23 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_24 | FAIL | OK | OK | FAIL | OK | OK | OK |
| request_25 | FAIL | OK | OK | FAIL | OK | OK | OK |

## Failure Details

### request_02

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `installments` |
| amount_safe_to_pay | `18081586.73` | `17229139.2` |
| payment_plan | `none` | `2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67` |

### request_03

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `1336857.68` | `873000` |
| earliest_date_for_full_payment | `2019-09-15` | `2019-11-15` |
| payment_plan | `2019-09-15:5491000` | `2019-11-15:5491000` |

### request_04

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `9025496.14` | `8401800` |

### request_05

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `not_affordable` |
| recommended_payment_method | `installments` | `not_recommended` |
| amount_safe_to_pay | `15488.0` | `737` |
| earliest_date_for_full_payment | `2025-11-06` | `` |
| payment_plan | `2025-11-06:15488` | `none` |

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
| earliest_date_for_full_payment | `2024-10-15` | `2024-10-23` |

### request_08

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_later` |
| recommended_payment_method | `not_recommended` | `wait` |
| amount_safe_to_pay | `0.0` | `284.57` |
| earliest_date_for_full_payment | `` | `2025-04-15` |
| payment_plan | `none` | `2025-04-15:996.60` |

### request_09

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `affordable_now` |
| recommended_payment_method | `installments` | `full_payment` |

### request_10

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `not_affordable` |
| recommended_payment_method | `installments` | `not_recommended` |
| amount_safe_to_pay | `266700.0` | `12700` |
| earliest_date_for_full_payment | `2024-12-06` | `` |
| payment_plan | `2024-12-06:266700` | `none` |

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
| payment_plan | `2026-04-05:65164` | `2026-04-19:22590.19|2026-05-20:22590.19|2026-06-20:22590.19` |

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
| amount_safe_to_pay | `504.39` | `597.74` |
| earliest_date_for_full_payment | `2025-09-15` | `` |
| payment_plan | `2025-08-04:504.39|2025-09-15:4909.81` | `none` |

### request_15

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `59.56` | `83.05` |

### request_16

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `affordable_with_plan` | `affordable_now` |
| recommended_payment_method | `installments` | `full_payment` |

### request_17

| Field | Predicted | Expected |
|:---|:---|:---|
| affordability_status | `not_affordable` | `affordable_with_plan` |
| recommended_payment_method | `not_recommended` | `installments` |
| amount_safe_to_pay | `210644.65` | `243849.58` |
| earliest_date_for_full_payment | `2026-05-15` | `2026-03-15` |
| payment_plan | `none` | `2026-03-01:95194.67|2026-03-31:95194.67|2026-04-30:95194.67` |

### request_18

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `698.96` | `462` |
| earliest_date_for_full_payment | `2026-08-15` | `2026-09-15` |
| payment_plan | `2026-08-15:3246.10` | `2026-09-15:3246.10` |

### request_19

| Field | Predicted | Expected |
|:---|:---|:---|
| recommended_payment_method | `installments` | `partial_payment` |
| amount_safe_to_pay | `39660.0` | `28820` |
| earliest_date_for_full_payment | `2024-09-04` | `2024-09-15` |
| payment_plan | `2024-09-04:39660` | `2024-09-04:28820|2024-09-15:10840` |

### request_20

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `21794.74` | `5400` |

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
| amount_safe_to_pay | `11899.37` | `9152` |

### request_24

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `16123.89` | `13420` |

### request_25

| Field | Predicted | Expected |
|:---|:---|:---|
| amount_safe_to_pay | `292156.18` | `1425000` |

## Failure Categories

| Category | Count | Request IDs |
|:---|:---:|:---|
| wrong_amount_safe | 21 | request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25 |
| wrong_earliest_date | 14 | request_03, request_05, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_17, request_18, request_19, request_21, request_22 |
| wrong_affordability_status | 12 | request_02, request_05, request_06, request_08, request_09, request_10, request_11, request_13, request_14, request_16, request_17, request_21 |
| wrong_payment_method | 10 | request_02, request_05, request_08, request_09, request_10, request_13, request_14, request_16, request_17, request_19 |
| wrong_plan_dates | 6 | request_03, request_05, request_08, request_10, request_13, request_18 |
| wrong_plan_entry_count | 5 | request_02, request_12, request_14, request_17, request_19 |
| wrong_spending_changes | 3 | request_06, request_11, request_21 |

## Systematic Patterns

- wrong_amount_safe: 21 request(s) — request_02, request_03, request_04, request_05, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_15, request_17, request_18, request_19, request_20, request_21, request_22, request_23, request_24, request_25
- wrong_earliest_date: 14 request(s) — request_03, request_05, request_06, request_07, request_08, request_10, request_11, request_13, request_14, request_17, request_18, request_19, request_21, request_22
- wrong_affordability_status: 12 request(s) — request_02, request_05, request_06, request_08, request_09, request_10, request_11, request_13, request_14, request_16, request_17, request_21
- wrong_payment_method: 10 request(s) — request_02, request_05, request_08, request_09, request_10, request_13, request_14, request_16, request_17, request_19
- wrong_plan_dates: 6 request(s) — request_03, request_05, request_08, request_10, request_13, request_18
- wrong_plan_entry_count: 5 request(s) — request_02, request_12, request_14, request_17, request_19
- wrong_spending_changes: 3 request(s) — request_06, request_11, request_21

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
| Runtime (s) | 5.0 |

