from decimal import Decimal
from uuid import uuid4


def process_mock_payment(amount: Decimal) -> str:
    if amount <= 0:
        raise ValueError("Payment amount must be positive")
    return f"mock-payment-{uuid4()}"