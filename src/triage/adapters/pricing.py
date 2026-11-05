"""Paid-tier list prices per 1M tokens, checked 2026-11-04 at aistudio.google.com/docs/pricing.
The free tier costs $0; this shows what the same usage would cost in production."""

_PRICES = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),  # promotional rate through 2026-12-31, then 1.50 / 7.50
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = _PRICES.get(model)
    if prices is None:
        return 0.0
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000
