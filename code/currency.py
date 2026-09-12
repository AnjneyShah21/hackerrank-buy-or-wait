"""
Currency conversion engine utilizing fixed dated exchange rates from exchange_rates.csv.
"""

from typing import List, Dict, Tuple, Optional
from code.models import ExchangeRate


class CurrencyConverter:
    """Manages currency conversions based on exchange_rates.csv."""

    def __init__(self, exchange_rates: Optional[List[ExchangeRate]] = None):
        # Key: (rate_date, from_currency, to_currency) -> rate
        self.exact_rates: Dict[Tuple[str, str, str], float] = {}
        # Key: (from_currency, to_currency) -> list of (rate_date, rate)
        self.pair_rates: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}

        if exchange_rates:
            self.load_rates(exchange_rates)

    def load_rates(self, exchange_rates: List[ExchangeRate]):
        """Indexes exchange rates for exact and nearest lookup."""
        self.exact_rates.clear()
        self.pair_rates.clear()

        for r in exchange_rates:
            key = (r.rate_date, r.from_currency, r.to_currency)
            self.exact_rates[key] = r.rate

            pair_key = (r.from_currency, r.to_currency)
            if pair_key not in self.pair_rates:
                self.pair_rates[pair_key] = []
            self.pair_rates[pair_key].append((r.rate_date, r.rate))

        # Sort dates ascending for each currency pair
        for pair_key in self.pair_rates:
            self.pair_rates[pair_key].sort(key=lambda x: x[0])

    def get_rate(self, from_currency: str, to_currency: str, date_str: str) -> float:
        """
        Retrieves the exact exchange rate for the given date and currency direction.
        If date is not exact, finds the nearest applicable rate for the currency pair.
        """
        if from_currency == to_currency:
            return 1.0

        exact_key = (date_str, from_currency, to_currency)
        if exact_key in self.exact_rates:
            return self.exact_rates[exact_key]

        # Check for month matching (YYYY-MM-15 matches YYYY-MM-DD)
        if len(date_str) >= 7:
            target_month = date_str[:7]
            pair_key = (from_currency, to_currency)
            if pair_key in self.pair_rates:
                for r_date, rate in self.pair_rates[pair_key]:
                    if r_date.startswith(target_month):
                        return rate

        # Fallback to nearest dated rate for this pair
        pair_key = (from_currency, to_currency)
        if pair_key in self.pair_rates and self.pair_rates[pair_key]:
            # Find closest date
            rates_by_date = self.pair_rates[pair_key]
            closest = min(rates_by_date, key=lambda x: abs(int(x[0].replace("-", "")) - int(date_str.replace("-", ""))))
            return closest[1]

        # Check inverse pair
        inv_pair = (to_currency, from_currency)
        if inv_pair in self.pair_rates and self.pair_rates[inv_pair]:
            inv_rate = self.get_rate(to_currency, from_currency, date_str)
            if inv_rate > 0:
                return 1.0 / inv_rate

        raise ValueError(f"No exchange rate found for {from_currency} -> {to_currency} on or near {date_str}")

    def convert(self, amount: float, from_currency: str, to_currency: str, date_str: str) -> float:
        """Converts an amount from one currency to another on a specific date."""
        if from_currency == to_currency:
            return amount
        rate = self.get_rate(from_currency, to_currency, date_str)
        return amount * rate
