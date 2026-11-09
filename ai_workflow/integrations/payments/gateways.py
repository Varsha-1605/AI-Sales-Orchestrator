"""Three simulated payment gateways. Pass failure="timeout" or "bank_declined" to force a failure."""

import asyncio
import random
from typing import Optional

from ai_workflow.integrations.payments.base import GatewayResult, PaymentGateway

FAILURE_TIMEOUT = "timeout"
FAILURE_BANK_DECLINED = "bank_declined"


class SimulatedGateway(PaymentGateway):
    def __init__(self, failure: Optional[str] = None, delay_seconds: float = 1.0):
        self.failure = failure
        self.delay_seconds = delay_seconds

    async def charge(self, amount: float) -> GatewayResult:
        await asyncio.sleep(self.delay_seconds)
        if self.failure == FAILURE_TIMEOUT:
            raise asyncio.TimeoutError
        if self.failure == FAILURE_BANK_DECLINED:
            return GatewayResult(success=False, reason="Bank declined")
        return GatewayResult(success=True, transaction_id=f"TXN{random.randint(100000, 999999)}")


class Razorpay(SimulatedGateway):
    name = "Razorpay"

    def __init__(self, failure: Optional[str] = FAILURE_TIMEOUT, delay_seconds: float = 1.2):
        super().__init__(failure, delay_seconds)


class PayU(SimulatedGateway):
    name = "PayU"

    def __init__(self, failure: Optional[str] = FAILURE_BANK_DECLINED, delay_seconds: float = 0.8):
        super().__init__(failure, delay_seconds)


class UpiDirect(SimulatedGateway):
    name = "UPI Direct"

    def __init__(self, failure: Optional[str] = None, delay_seconds: float = 0.7):
        super().__init__(failure, delay_seconds)


GATEWAYS = {gateway.name: gateway for gateway in [Razorpay(), PayU(), UpiDirect()]}
