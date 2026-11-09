"""What every payment gateway must provide."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class GatewayResult:
    success: bool
    reason: str = ""
    transaction_id: Optional[str] = None
    seconds: float = 0.0


class PaymentGateway(ABC):
    name: str

    @abstractmethod
    async def charge(self, amount: float) -> GatewayResult:
        """Try to take the payment. A gateway may also raise TimeoutError."""
