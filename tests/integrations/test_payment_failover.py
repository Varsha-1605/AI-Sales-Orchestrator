from ai_workflow.integrations.payments.charge import charge
from ai_workflow.integrations.payments.gateways import GATEWAYS, PayU, Razorpay, UpiDirect
from ai_workflow.settings import settings


async def test_first_gateway_succeeds(monkeypatch):
    monkeypatch.setitem(GATEWAYS, "Razorpay", Razorpay(failure=None, delay_seconds=0))

    result = await charge(1000)

    assert result["success"] is True
    assert result["gateway"] == "Razorpay"
    assert len(result["attempts"]) == 1


async def test_fails_over_to_the_second_gateway(monkeypatch):
    monkeypatch.setitem(GATEWAYS, "PayU", PayU(failure=None, delay_seconds=0))

    result = await charge(1000)

    assert result["gateway"] == "PayU"
    assert [a["status"] for a in result["attempts"]] == ["failed", "success"]
    assert result["attempts"][0]["reason"] == "Timeout error"


async def test_fails_over_to_the_third_gateway_and_reports_each_attempt():
    tried = []

    async def on_attempt(gateway, result):
        tried.append((gateway, result.success))

    result = await charge(1000, on_attempt=on_attempt)

    assert result["gateway"] == "UPI Direct"
    assert tried == [("Razorpay", False), ("PayU", False), ("UPI Direct", True)]
    assert result["transaction_id"].startswith("TXN")


async def test_all_gateways_failing_returns_a_failure(monkeypatch):
    monkeypatch.setitem(GATEWAYS, "UPI Direct", UpiDirect(failure="bank_declined", delay_seconds=0))

    result = await charge(1000)

    assert result["success"] is False
    assert len(result["attempts"]) == 3
    assert "All payment methods failed" in result["message"]


async def test_a_slow_gateway_counts_as_a_timeout(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_GATEWAY_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setitem(GATEWAYS, "Razorpay", Razorpay(failure=None, delay_seconds=1))

    result = await charge(1000)

    assert result["attempts"][0] == {"gateway": "Razorpay", "status": "failed", "reason": "Timeout error"}
    assert result["gateway"] == "UPI Direct"
