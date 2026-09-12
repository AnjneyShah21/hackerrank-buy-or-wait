# Buy or Wait? Solution Architecture

Modular, production-grade financial reasoning agent built for HackerRank Orchestrate (September 2026).

## Directory Structure

```text
code/
├── main.py                  # Primary entry point orchestrating full pipeline
├── config.py                # File paths, simulation constants, and schema enums
├── models.py                # Strongly-typed domain data structures
├── data_loader.py           # Robust CSV parser for all input dataset files
├── currency.py              # Exact dated exchange rate conversion engine
├── evidence.py              # Structured evidence store & conflict resolution rules
├── image_extractor.py       # Vision / OCR extraction for images (missing amounts)
├── message_interpreter.py   # Multilingual NLP parser for messages (English & Indonesian)
├── forecast.py              # 90-day daily cash-flow simulator & min balance checker
├── financial_engine.py      # Computes amount_safe_to_pay & earliest_date_for_full_payment
├── payment_planner.py       # Generates candidate full/partial/installment/wait plans
├── decision_engine.py       # Strict multi-tier ranker & grounded explanation builder
├── validator.py             # Deterministic invariant checker & schema gatekeeper
├── output_writer.py         # Formats and outputs root-level output.csv
├── prompts/                 # Prompt templates for extraction & explanation
│   ├── financial_evidence.txt
│   ├── image_extraction.txt
│   └── explanation.txt
├── evaluation/              # Benchmark evaluator and usage reporting
│   ├── main.py
│   ├── metrics.py
│   ├── error_analysis.py
│   ├── evaluation_report.md
│   └── usage_report.md
└── tests/                   # Comprehensive unit test suite
    ├── test_data_loader.py
    ├── test_currency.py
    ├── test_forecast.py
    ├── test_payment_plans.py
    ├── test_validator.py
    └── test_edge_cases.py
```

## Running the Solution

From the repository root:

```bash
python code/main.py
```

## Running the Evaluation Suite

```bash
python code/evaluation/main.py
```

## Running Unit Tests

```bash
python -m unittest discover code/tests
```
