"""
Currency conversion engine utilizing fixed dated exchange rates from exchange_rates.csv.
Provides deterministic, auditable FX conversions with precision protection.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from code.models import ConversionAudit, ExchangeRate


class CurrencyConverter:
    """Manages deterministic currency conversions based on exchange_rates.csv."""

    def __init__(self, exchange_rates: Optional[List[ExchangeRate]] = None):
        # Key: (rate_date, from_currency, to_currency) -> rate
        self.exact_rates: Dict[Tuple[str, str, str], float] = {}
        # Key: (from_currency, to_currency) -> list of (rate_date, rate)
        self.pair_rates: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
        # O(1) cache for resolved rates: (from_curr, to_curr, date_str) -> (rate, rate_date_used, method)
        self._resolved_rate_cache: Dict[Tuple[str, str, str], Tuple[float, str, str]] = {}

        if exchange_rates:
            self.load_rates(exchange_rates)

    def load_rates(self, exchange_rates: List[ExchangeRate]):
        """Indexes exchange rates for exact and nearest-date lookups."""
        self.exact_rates.clear()
        self.pair_rates.clear()
        self._resolved_rate_cache.clear()

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

    def resolve_rate(
        self, from_currency: str, to_currency: str, date_str: str
    ) -> Tuple[float, str, str]:
        """
        Determines the exact or nearest exchange rate, rate date used, and lookup method.
        Returns: (rate, rate_date_used, lookup_method)
        Raises: ValueError if no valid conversion path exists.
        """
        from_curr = from_currency.strip().upper()
        to_curr = to_currency.strip().upper()

        if from_curr == to_curr:
            return 1.0, date_str, "identity"

        cache_key = (from_curr, to_curr, date_str[:10])
        if cache_key in self._resolved_rate_cache:
            return self._resolved_rate_cache[cache_key]

        # 1. Exact match for direct pair
        exact_key = (date_str, from_curr, to_curr)
        if exact_key in self.exact_rates:
            res = (self.exact_rates[exact_key], date_str, "exact")
            self._resolved_rate_cache[cache_key] = res
            return res

        # 2. Exact match for inverse pair
        inv_exact_key = (date_str, to_curr, from_curr)
        if inv_exact_key in self.exact_rates:
            inv_rate = self.exact_rates[inv_exact_key]
            if inv_rate > 0:
                res = (round(1.0 / inv_rate, 8), date_str, "inverse_exact")
                self._resolved_rate_cache[cache_key] = res
                return res

        # Helper to parse date string for distance calculation
        try:
            target_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            target_dt = datetime(2026, 1, 1)

        # 3. Nearest date lookup for direct pair
        pair_key = (from_curr, to_curr)
        if pair_key in self.pair_rates and self.pair_rates[pair_key]:
            rates = self.pair_rates[pair_key]
            closest = min(
                rates,
                key=lambda x: abs(
                    (datetime.strptime(x[0], "%Y-%m-%d") - target_dt).days
                ),
            )
            res = (closest[1], closest[0], "nearest_date")
            self._resolved_rate_cache[cache_key] = res
            return res

        # 4. Nearest date lookup for inverse pair
        inv_pair_key = (to_curr, from_curr)
        if inv_pair_key in self.pair_rates and self.pair_rates[inv_pair_key]:
            rates = self.pair_rates[inv_pair_key]
            closest = min(
                rates,
                key=lambda x: abs(
                    (datetime.strptime(x[0], "%Y-%m-%d") - target_dt).days
                ),
            )
            if closest[1] > 0:
                res = (round(1.0 / closest[1], 8), closest[0], "inverse_nearest")
                self._resolved_rate_cache[cache_key] = res
                return res

        raise ValueError(
            f"No exchange rate found for {from_curr} -> {to_curr} on or near {date_str}"
        )

    def get_rate(self, from_currency: str, to_currency: str, date_str: str) -> float:
        """Retrieves the exchange rate factor for the currency pair and date."""
        rate, _, _ = self.resolve_rate(from_currency, to_currency, date_str)
        return rate

    def convert_with_audit(
        self, amount: float, from_currency: str, to_currency: str, date_str: str
    ) -> ConversionAudit:
        """
        Converts amount from from_currency to to_currency with full audit metadata.
        Protects against floating point precision accumulation errors.
        """
        from_curr = from_currency.strip().upper()
        to_curr = to_currency.strip().upper()

        if from_curr == to_curr:
            return ConversionAudit(
                original_amount=amount,
                from_currency=from_curr,
                to_currency=to_curr,
                date_str=date_str,
                rate_used=1.0,
                rate_date_used=date_str,
                lookup_method="identity",
                converted_amount=round(amount, 4),
            )

        rate, rate_date_used, method = self.resolve_rate(from_curr, to_curr, date_str)
        converted = round(amount * rate, 4)

        return ConversionAudit(
            original_amount=amount,
            from_currency=from_curr,
            to_currency=to_curr,
            date_str=date_str,
            rate_used=rate,
            rate_date_used=rate_date_used,
            lookup_method=method,
            converted_amount=converted,
        )

    def convert(
        self, amount: float, from_currency: str, to_currency: str, date_str: str
    ) -> float:
        """Converts amount from from_currency to to_currency on date_str."""
        audit = self.convert_with_audit(amount, from_currency, to_currency, date_str)
        return audit.converted_amount
