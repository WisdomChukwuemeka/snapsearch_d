import anthropic
import json
import re
from django.conf import settings


client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ─────────────────────────────────────────────────────────────
# Helper: parse data URL or raw base64
# ─────────────────────────────────────────────────────────────
def _parse_image_data(image_data: str):
    """
    Accepts EITHER:
      • Full data URL  →  "data:image/png;base64,XXXX..."
      • Raw base64     →  "XXXX..."  (assumes image/jpeg)

    Returns (clean_base64_string, media_type)
    Raises ValueError if the input is empty or malformed.
    """
    if not image_data or not image_data.strip():
        raise ValueError("Empty image data received — nothing was sent to Claude.")

    image_data = image_data.strip()

    if image_data.startswith("data:"):
        match = re.match(r"data:(image/[\w+\-]+);base64,(.+)", image_data, re.DOTALL)
        if not match:
            raise ValueError(
                f"Malformed data URL. Expected 'data:image/...;base64,...' "
                f"but got: {image_data[:80]}"
            )
        media_type = match.group(1)   # e.g. "image/png"
        b64_data   = match.group(2).strip()
        return b64_data, media_type

    # Raw base64 fallback — assume JPEG
    return image_data, "image/jpeg"


# ─────────────────────────────────────────────────────────────
# Main: analyze product image
# ─────────────────────────────────────────────────────────────
def analyze_image_for_product(image_base64: str, query_type: str) -> dict:
    """
    Uses Claude to analyze an uploaded product image.
    Returns structured JSON based on query_type: 'buy', 'learn', or 'others'.
    """

    # Parse image FIRST — fail fast with a clear message
    try:
        b64_data, media_type = _parse_image_data(image_base64)
    except ValueError as e:
        print(f"[SnapSearch] ❌ Image parse error: {e}")
        return {
            "error": str(e),
            "product_name": "Unknown Product",
            "suppliers": [],
        }

    print(f"[SnapSearch] ✅ Image ready — media_type={media_type}, b64_len={len(b64_data)}")

    system_prompt = """You are SnapSearch AI — a world-class product intelligence engine.
You analyze product images with exceptional accuracy and return structured JSON.
Always respond with valid JSON only. No markdown, no explanation outside the JSON.
Be thorough, accurate, and commercially useful."""

    if query_type == "buy":
        user_prompt = """Analyze this product image and return a JSON object for the "buy" flow.

Return this exact structure:
{
  "product_name": "Exact product name",
  "category": "Product category",
  "brand": "Brand if visible or detectable",
  "confidence": "high|medium|low",
  "suppliers": [
    {
      "platform": "amazon",
      "company_name": "Amazon",
      "product_title": "Specific product title matching the image",
      "type": "Retail",
      "country": "USA",
      "price": "$XX.XX",
      "rating": "4.5",
      "review_count": 15230,
      "affiliate_url": "https://www.amazon.com/s?k=PRODUCT+NAME+ENCODED&tag=snapsearch-20",
      "image_url": ""
    },
    {
      "platform": "aliexpress",
      "company_name": "AliExpress",
      "product_title": "Product title",
      "type": "Wholesale & Retail",
      "country": "China",
      "price": "$X.XX - $XX.XX",
      "rating": "4.3",
      "review_count": 8902,
      "affiliate_url": "https://www.aliexpress.com/wholesale?SearchText=PRODUCT+NAME",
      "image_url": ""
    },
    {
      "platform": "ebay",
      "company_name": "eBay",
      "product_title": "Product title",
      "type": "Marketplace",
      "country": "USA",
      "price": "$XX.XX",
      "rating": "4.2",
      "review_count": 3421,
      "affiliate_url": "https://www.ebay.com/sch/i.html?_nkw=PRODUCT+NAME",
      "image_url": ""
    }
  ],
  "countries_available": ["USA", "UK", "Germany", "Japan", "Nigeria", "China", "Canada", "Australia"]
}

For affiliate_url fields: use actual working search URLs with the real product name URL-encoded.
List 3-6 suppliers across platforms. Include real price ranges you know for this type of product."""

    elif query_type == "learn":
        user_prompt = """Analyze this product image and return a JSON object for the "learn" flow.

Return this exact structure:
{
  "product_name": "Exact product name",
  "category": "Product category",
  "confidence": "high|medium|low",
  "history": "Write 4-6 detailed paragraphs about the complete history of this product. Include origin, invention, evolution, cultural impact, major milestones. Make it rich and informative. Separate paragraphs with \\n\\n.",
  "description": "Write 4-6 detailed paragraphs describing everything visible on the product label and packaging. Include ingredients/components, nutritional info if food, specifications if tech, materials, certifications, warnings, country of manufacture, net weight/volume, usage instructions. Separate with \\n\\n.",
  "production": {
    "overview": {
      "Difficulty": "Beginner|Intermediate|Advanced",
      "Time to Produce": "X weeks/months/years",
      "Scale": "Home|Small Farm|Industrial",
      "Estimated Cost": "$X - $X"
    },
    "steps": [
      {
        "title": "Step title",
        "detail": "Comprehensive, accurate detail for this step. Include specific measurements, temperatures, durations, equipment needed.",
        "timing": "Duration or timing note"
      }
    ]
  }
}

For farm/food products: include medication schedules, feed types and timing, breeding methods, maturity periods, harvest techniques.
For manufactured goods: include raw materials, manufacturing process, quality control, assembly.
Include 8-15 production steps minimum. Be genuinely useful and accurate."""

    else:  # others
        user_prompt = """Analyze this product image and identify it precisely.

Return this exact JSON:
{
  "product_name": "Exact product name",
  "category": "Category",
  "confidence": "high|medium|low",
  "initial_context": "A 2-sentence description of what you see in the image, to help with follow-up questions."
}"""

    try:
        message = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,   # ✅ dynamic — not hardcoded
                                "data": b64_data,            # ✅ clean base64 — no prefix
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()
        print(f"[SnapSearch] Claude response preview: {raw[:300]}")

        # Strip markdown code fences if Claude wraps in ```json ... ```
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"[SnapSearch] ❌ JSON parse error: {e}\nFull raw response:\n{raw}")
        return {
            "error": f"JSON parse error: {str(e)}",
            "product_name": "Unknown Product",
            "suppliers": [],
        }
    except Exception as e:
        print(f"[SnapSearch] ❌ Claude API error: {type(e).__name__}: {e}")
        return {
            "error": str(e),
            "product_name": "Unknown Product",
            "suppliers": [],
        }


# ─────────────────────────────────────────────────────────────
# Follow-up: answer free-form product questions
# ─────────────────────────────────────────────────────────────
def answer_product_question(
    prompt: str,
    product_context: str,
    image_base64: str,
    conversation_history: list,
) -> str:
    """
    Answers a free-form question about a product using Claude with image context.
    Maintains conversation history for multi-turn chat.
    """

    try:
        b64_data, media_type = _parse_image_data(image_base64)
    except ValueError as e:
        print(f"[SnapSearch] ❌ Image parse error in ask: {e}")
        return f"Could not process the image: {str(e)}"

    system = f"""You are SnapSearch AI, an expert product analyst assistant.
The user has uploaded an image of: {product_context or 'a product'}.
Answer their questions accurately, thoroughly, and helpfully.
Draw on your knowledge of this product type. Be specific, not vague.
If asked about pricing, suppliers, regulations, or market data — give real, current estimates.
Format your answer clearly. Use line breaks for readability."""

    # Build message history (keep last 10 for context window)
    messages = []
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Append the current question with the image
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,   # ✅ dynamic
                    "data": b64_data,            # ✅ clean
                },
            },
            {"type": "text", "text": prompt},
        ],
    })

    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2000,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        print(f"[SnapSearch] ❌ answer_product_question error: {type(e).__name__}: {e}")
        return f"Sorry, I couldn't process that question. Error: {str(e)}"