"""Take a payment, moving to the next gateway when one fails."""

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from loguru import logger

from ai_workflow.integrations.payments.base import GatewayResult
from ai_workflow.integrations.payments.gateways import GATEWAYS
from ai_workflow.settings import settings

AttemptCallback = Callable[[str, GatewayResult], Awaitable[None]]


async def charge(amount: float, on_attempt: Optional[AttemptCallback] = None) -> Dict[str, Any]:
    """Try the gateways in PAYMENT_GATEWAY_ORDER until one succeeds."""
    attempts = []
    total_seconds = 0.0
    for name in settings.PAYMENT_GATEWAY_ORDER:
        started = time.monotonic()
        try:
            result = await asyncio.wait_for(
                GATEWAYS[name].charge(amount), timeout=settings.PAYMENT_GATEWAY_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            result = GatewayResult(success=False, reason="Timeout error")
        result.seconds = time.monotonic() - started
        total_seconds += result.seconds
        logger.info("Payment via {}: {}", name, "success" if result.success else result.reason)

        attempts.append({
            "gateway": name,
            "status": "success" if result.success else "failed",
            "reason": result.reason,
        })
        if on_attempt:
            await on_attempt(name, result)

        if result.success:
            return {
                "success": True,
                "amount": amount,
                "gateway": name,
                "transaction_id": result.transaction_id,
                "attempts": attempts,
                "total_time": f"{total_seconds:.1f}s",
                "message": f"Payment successful via {name}!",
            }

    return {
        "success": False,
        "amount": amount,
        "attempts": attempts,
        "total_time": f"{total_seconds:.1f}s",
        "message": "All payment methods failed. Please try again later.",
    }
