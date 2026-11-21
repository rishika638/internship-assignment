"""Official LLM Provider Pricing Table and Cost Calculation Utility.
Prices referenced from official provider pricing documentation (as of late 2024 / 2025).
"""
from typing import Dict, Tuple

# Rates per 1,000,000 tokens (USD)
# (Input price per 1M, Output price per 1M)
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # Gemini
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4-turbo": (10.00, 30.00),
    
    # Anthropic Claude
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    
    # Mock / Fallback
    "mock-provider": (0.00, 0.00),
}

def calculate_llm_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the estimated cost in USD based on input and output token counts."""
    # Find matching pricing key
    matched_pricing = None
    model_lower = model_name.lower()
    for key, price in MODEL_PRICING.items():
        if key in model_lower:
            matched_pricing = price
            break
            
    if not matched_pricing:
        matched_pricing = (0.15, 0.60)  # Default fallback to commodity tier

    input_price_per_1m, output_price_per_1m = matched_pricing
    cost = (input_tokens / 1_000_000.0) * input_price_per_1m + (output_tokens / 1_000_000.0) * output_price_per_1m
    return round(cost, 6)
