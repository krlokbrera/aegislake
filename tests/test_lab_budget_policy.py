import importlib.util
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location(
    "lab_budget_policy", Path(__file__).parents[1] / "scripts" / "lab_budget_policy.py"
)
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)


class CreditPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 2, tzinfo=timezone.utc)
        self.options = dict(
            hourly_ceiling_eur="0.15", residual_disk_eur="7.50",
            deadline_utc=self.now + timedelta(days=7), now_utc=self.now,
        )

    def document(self, value="50", currency="EUR"):
        return {"properties": {"billingCurrency": "EUR", "balanceSummary": {
            "estimatedBalanceInBillingCurrency": {"currency": currency, "value": value}
        }}}

    def decision(self, document):
        return policy.decide(document, **self.options)

    def test_continue_only_above_reserve_and_lag_and_disk_cost(self):
        self.assertFalse(self.decision(self.document("50")).stop)
        self.assertEqual(self.decision(self.document("50")).threshold_eur, Decimal("28.30"))

    def test_exact_threshold_stops(self):
        self.assertTrue(self.decision(self.document("28.30")).stop)

    def test_current_balance_does_not_override_smaller_estimate(self):
        doc = self.document("9")
        doc["properties"]["balanceSummary"]["currentBalance"] = {"currency":"USD","value":100}
        self.assertEqual(self.decision(doc).reason, "credit_reserve")

    def test_wrong_currency_fails_closed(self):
        self.assertEqual(self.decision(self.document("100", "USD")).reason, "unreadable_credit")

    def test_missing_balance_fails_closed(self):
        self.assertTrue(self.decision({}).stop)

    def test_invalid_balances_fail_closed(self):
        for value in [None, True, "NaN", "Infinity", "-1", "n/a", {}, []]:
            with self.subTest(value=value):
                self.assertEqual(self.decision(self.document(value)).reason, "unreadable_credit")

    def test_deadline_stops_even_with_large_balance(self):
        self.options["deadline_utc"] = self.now
        self.assertEqual(self.decision(self.document("100")).reason, "hard_deadline")

    def test_naive_deadline_is_rejected(self):
        self.options["deadline_utc"] = self.now.replace(tzinfo=None)
        with self.assertRaises(ValueError):
            self.decision(self.document())

    def test_invalid_price_is_rejected(self):
        self.options["hourly_ceiling_eur"] = 0
        with self.assertRaises(ValueError):
            self.decision(self.document())

    def test_reserve_cannot_be_lowered_below_ten(self):
        with self.assertRaises(ValueError):
            policy.decide(self.document(), **self.options, reserve_eur=9)

    def test_explicit_non_euro_billing_fails_closed(self):
        doc = self.document()
        doc["properties"]["billingCurrency"] = "USD"
        self.assertTrue(self.decision(doc).stop)


if __name__ == "__main__":
    unittest.main()
