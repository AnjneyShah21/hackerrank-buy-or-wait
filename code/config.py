"""
Configuration settings and global constants for the Buy or Wait? system.
"""

import os
from pathlib import Path

# Paths configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "dataset"
MEDIA_DIR = DATASET_DIR / "media"
IMAGES_DIR = MEDIA_DIR / "images"
PROMPTS_DIR = CODE_DIR / "prompts"
EVALUATION_DIR = CODE_DIR / "evaluation"

# Input dataset file paths
REQUESTS_CSV = DATASET_DIR / "requests.csv"
SAMPLE_REQUESTS_CSV = DATASET_DIR / "sample_requests.csv"
FINANCIAL_PROFILES_CSV = DATASET_DIR / "financial_profiles.csv"
FINANCIAL_EVENTS_CSV = DATASET_DIR / "financial_events.csv"
EXCHANGE_RATES_CSV = DATASET_DIR / "exchange_rates.csv"
REQUEST_PAYMENT_OPTIONS_CSV = DATASET_DIR / "request_payment_options.csv"
MESSAGES_CSV = DATASET_DIR / "messages.csv"
IMAGES_CSV = DATASET_DIR / "images.csv"
OUTPUT_TEMPLATE_CSV = DATASET_DIR / "output.csv"

# Target output CSV path (in repository root as required)
OUTPUT_CSV = PROJECT_ROOT / "output.csv"

# Simulation Constants
FORECAST_DAYS = 90
MAX_SPENDING_CHANGES = 3

# Allowed Enums & Formats
VALID_AFFORDABILITY_STATUSES = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

VALID_PAYMENT_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}

VALID_REQUEST_TYPES = {
    "purchase",
    "travel",
    "education",
    "family_transfer",
    "debt_repayment",
    "investment",
    "housing",
    "emergency_expense",
    "other",
}

OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

# Supported Currencies
SUPPORTED_CURRENCIES = {"INR", "EUR", "IDR", "ZAR", "USD"}

# Environment Configuration
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
USE_AI_VISION = os.getenv("USE_AI_VISION", "false").lower() in ("true", "1", "yes")
USE_AI_NLP = os.getenv("USE_AI_NLP", "false").lower() in ("true", "1", "yes")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
