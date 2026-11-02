"""Conservative credit decision; no Azure writes or credentials."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone


@dataclass(frozen=True)
class Decision:
    stop: bool
    reason: str
    balance_eur: Decimal | None
    threshold_eur: Decimal


def money(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not an amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Expected finite nonnegative amount")
    return amount


def balance_eur(document):
    """Use only the provider's explicit EUR estimate, never treat USD as EUR."""
    properties = document["properties"]
    if properties["billingCurrency"] != "EUR":
        raise ValueError("Expected EUR billing")
    amount = properties["balanceSummary"]["estimatedBalanceInBillingCurrency"]
    if amount["currency"] != "EUR":
        raise ValueError("Balance currency must be EUR")
    return money(amount["value"])


def decide(document, *, hourly_ceiling_eur, residual_disk_eur,
           deadline_utc, now_utc=None, reserve_eur=10, lag_hours=72):
    """Fail closed, reserving delayed compute charges and retained disk costs.

    The caller must independently verify prices, the deadline and shutdown.
    This calculation cannot guarantee an exact balance or control other workloads.
    """
    reserve = money(reserve_eur)
    hourly = money(hourly_ceiling_eur)
    residual = money(residual_disk_eur)
    lag = money(lag_hours)
    if reserve < 10 or lag < 24 or hourly == 0:
        raise ValueError("Reserve >=10, lag >=24 and positive price required")
    threshold = reserve + hourly * lag + residual
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None or deadline_utc.tzinfo is None:
        raise ValueError("Timezone-aware times required")
    if now >= deadline_utc:
        return Decision(True, "hard_deadline", None, threshold)
    try:
        balance = balance_eur(document)
    except (KeyError, TypeError, ValueError):
        return Decision(True, "unreadable_credit", None, threshold)
    if balance <= threshold:
        return Decision(True, "credit_reserve", balance, threshold)
    return Decision(False, "within_budget", balance, threshold)
