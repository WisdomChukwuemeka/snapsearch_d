"""
geminiSearch/ai_service.py

Supports THREE AI providers — all switchable per-request or globally:

  • "gemini"    — Google Gemini 2.0 Flash       (best all-round, default)
  • "anthropic" — Anthropic Claude Opus          (highest accuracy)
  • "vision"    — Google Cloud Vision API        (label/object/logo detection
                   + Gemini for structured output)

How Google Cloud Vision works here:
  1. Cloud Vision detects labels, objects, logos, text from the image
  2. That detection data is fed as context into Gemini to produce the
     same structured JSON output your frontend already expects.
  This gives you Vision's precision with Gemini's structured response.

Switch provider:
  • Per-request:  pass provider="vision" in the POST body
  • Globally:     set PREFERRED_AI_PROVIDER=vision in .env / settings.py

Google Cloud Vision auth (service account JSON):
  Add to .env:  GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/your-service-account.json
  OR set in settings.py: GOOGLE_APPLICATION_CREDENTIALS = os.getenv(...)
  The SDK reads this env var automatically — no other code changes needed.
"""

import json
import re
import base64
import os
import anthropic
from django.conf import settings

from google import genai
from google.genai import types

gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)


# ── Initialise Gemini + Anthropic clients once at module load ─────────────────
anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Default provider — override in settings.py: PREFERRED_AI_PROVIDER = "vision"
DEFAULT_PROVIDER = getattr(settings, "PREFERRED_AI_PROVIDER", "gemini")

VALID_PROVIDERS = ("gemini", "anthropic", "vision")

# ── Gemini model name — single place to update if Google changes it ───────────
GEMINI_MODEL = "gemini-2.0-flash"


# ─────────────────────────────────────────────────────────────────────────────
# Google Cloud Vision client (lazy — only imported when provider="vision")
# ─────────────────────────────────────────────────────────────────────────────
def _get_vision_client():
    """
    Build a Google Cloud Vision client using service account JSON.
    Reads the credentials file path from:
      1. settings.GOOGLE_APPLICATION_CREDENTIALS  (set via .env)
      2. OS environment variable GOOGLE_APPLICATION_CREDENTIALS (SDK default)

    .env example:
      GOOGLE_APPLICATION_CREDENTIALS=C:/Users/user/Downloads/snapsearchbase/backend/geminiSearch/config/your-service-account.json
    """
    from google.cloud import vision as gcloud_vision

    creds_path = getattr(settings, "GVS_CREDENTIALS", None) \
                 or os.environ.get("GVS_CREDENTIALS")

    if creds_path:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            creds_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return gcloud_vision.ImageAnnotatorClient(credentials=credentials)

    # Fallback: let the SDK find credentials automatically
    # (works if GOOGLE_APPLICATION_CREDENTIALS is already in the OS environment)
    return gcloud_vision.ImageAnnotatorClient()


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────
def _parse_image_data(image_data: str):
    """
    Accepts EITHER:
      • Full data URL  →  "data:image/png;base64,XXXX..."
      • Raw base64     →  "XXXX..."  (assumes image/jpeg)

    Returns (clean_base64_string, mime_type)
    Raises ValueError if the input is empty or malformed.
    """
    if not image_data or not image_data.strip():
        raise ValueError("Empty image data received.")

    image_data = image_data.strip()

    if image_data.startswith("data:"):
        match = re.match(r"data:(image/[\w+\-]+);base64,(.+)", image_data, re.DOTALL)
        if not match:
            raise ValueError(
                f"Malformed data URL. Expected 'data:image/...;base64,...' "
                f"but got: {image_data[:80]}"
            )
        return match.group(2).strip(), match.group(1)   # b64_data, mime_type

    return image_data.strip(), "image/jpeg"             # raw base64 fallback


def _clean_json(raw: str) -> str:
    """Strip markdown code fences before JSON parsing."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Shared prompts (used by all three providers)
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are SnapSearch AI — a world-class product intelligence engine. "
    "You analyze product images with exceptional accuracy and return structured JSON. "
    "Always respond with valid JSON only. No markdown, no explanation outside the JSON. "
    "Be thorough, accurate, and commercially useful."
)

BUY_PROMPT = """Analyze this product image and return a JSON object for the "buy" flow.

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

For affiliate_url: use actual working search URLs with the real product name URL-encoded.
List 3-6 suppliers across platforms. Include real price ranges you know for this type of product."""

LEARN_PROMPT = """Analyze this product image and return a JSON object for the "learn" flow.

Return this exact structure:
{
  "product_name": "Exact product name",
  "category": "Product category",
  "confidence": "high|medium|low",
  "history": "Write 4-6 detailed paragraphs about the complete history of this product. Include origin, invention, evolution, cultural impact, major milestones. Separate paragraphs with \\n\\n.",
  "description": "Write 4-6 detailed paragraphs describing everything visible on the product. Include ingredients/components, nutritional info if food, specifications if tech, materials, certifications, warnings. Separate with \\n\\n.",
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
        "detail": "Comprehensive, accurate detail. Include measurements, temperatures, durations, equipment.",
        "timing": "Duration or timing note"
      }
    ]
  }
}

Include 8-15 production steps minimum. Be genuinely useful and accurate."""

OTHERS_PROMPT = """Analyze this product image and identify it precisely.

Return this exact JSON:
{
  "product_name": "Exact product name",
  "category": "Category",
  "confidence": "high|medium|low",
  "initial_context": "A 2-sentence description of what you see in the image."
}"""


def _get_user_prompt(query_type: str) -> str:
    if query_type == "buy":
        return BUY_PROMPT
    elif query_type == "learn":
        return LEARN_PROMPT
    return OTHERS_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# Provider 1: Gemini
# ─────────────────────────────────────────────────────────────────────────────
def _gemini_analyze(b64_data: str, mime_type: str, user_prompt: str) -> dict:
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=base64.b64decode(b64_data), mime_type=mime_type),
            user_prompt,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=4000,
            temperature=0.2,
        ),
    )
    return json.loads(_clean_json(response.text))


def _gemini_ask(
    b64_data: str,
    mime_type: str,
    prompt: str,
    product_context: str,
    conversation_history: list,
) -> str:
    system = (
        f"You are SnapSearch AI, an expert product analyst. "
        f"The user uploaded an image of: {product_context or 'a product'}. "
        f"Answer accurately, thoroughly, and helpfully. Use line breaks for readability."
    )
    model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=system)

    history = []
    for msg in conversation_history[-10:]:
        role = "model" if msg["role"] == "assistant" else "user"
        if isinstance(msg["content"], str):
            history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=history)
    image_part = {"inline_data": {"mime_type": mime_type, "data": b64_data}}
    response = chat.send_message(
        [image_part, prompt],
        generation_config=genai.GenerationConfig(max_output_tokens=2000, temperature=0.4),
    )
    return response.text


# ─────────────────────────────────────────────────────────────────────────────
# Provider 2: Anthropic
# ─────────────────────────────────────────────────────────────────────────────
def _anthropic_analyze(b64_data: str, mime_type: str, user_prompt: str) -> dict:
    message = anthropic_client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_data}},
                {"type": "text",  "text": user_prompt},
            ],
        }],
    )
    return json.loads(_clean_json(message.content[0].text))


def _anthropic_ask(
    b64_data: str,
    mime_type: str,
    prompt: str,
    product_context: str,
    conversation_history: list,
) -> str:
    system = (
        f"You are SnapSearch AI, an expert product analyst. "
        f"The user uploaded an image of: {product_context or 'a product'}. "
        f"Answer accurately, thoroughly, and helpfully. Use line breaks for readability."
    )
    messages = []
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_data}},
            {"type": "text",  "text": prompt},
        ],
    })
    response = anthropic_client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=2000,
        system=system,
        messages=messages,
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# Provider 3: Google Cloud Vision + Gemini
# ─────────────────────────────────────────────────────────────────────────────
def _vision_detect(b64_data: str) -> dict:
    """
    Calls Google Cloud Vision using service account JSON credentials.
    Runs: LABEL_DETECTION, OBJECT_LOCALIZATION, LOGO_DETECTION,
          TEXT_DETECTION, WEB_DETECTION.
    """
    from google.cloud import vision as gcloud_vision

    client = _get_vision_client()
    image  = gcloud_vision.Image(content=base64.b64decode(b64_data))

    response = client.annotate_image({
        "image": image,
        "features": [
            {"type_": gcloud_vision.Feature.Type.LABEL_DETECTION,      "max_results": 15},
            {"type_": gcloud_vision.Feature.Type.OBJECT_LOCALIZATION,  "max_results": 10},
            {"type_": gcloud_vision.Feature.Type.LOGO_DETECTION,       "max_results":  5},
            {"type_": gcloud_vision.Feature.Type.TEXT_DETECTION,       "max_results":  1},
            {"type_": gcloud_vision.Feature.Type.WEB_DETECTION,        "max_results": 10},
        ],
    })

    labels  = [l.description for l in response.label_annotations  if l.score  > 0.6]
    objects = [o.name        for o in response.localized_object_annotations]
    logos   = [l.description for l in response.logo_annotations]

    texts = []
    if response.text_annotations:
        texts = [
            line.strip()
            for line in response.text_annotations[0].description.splitlines()
            if line.strip()
        ][:10]

    web_entities = []
    if response.web_detection and response.web_detection.web_entities:
        web_entities = [
            e.description
            for e in response.web_detection.web_entities
            if e.score > 0.5 and e.description
        ][:10]

    best_guess = ""
    if response.web_detection and response.web_detection.best_guess_labels:
        best_guess = response.web_detection.best_guess_labels[0].label

    return {
        "labels":       labels,
        "objects":      objects,
        "logos":        logos,
        "texts":        texts,
        "web_entities": web_entities,
        "best_guess":   best_guess,
    }


def _vision_analyze(b64_data: str, mime_type: str, user_prompt: str) -> dict:
    """
    Step 1: Google Cloud Vision extracts labels/objects/logos/text from the image.
    Step 2: Gemini uses those signals as context to produce structured JSON output.
    """
    print("[geminiSearch] 🔍 Running Google Cloud Vision detection...")
    vision_data = _vision_detect(b64_data)

    print(
        f"[geminiSearch] Vision signals — "
        f"best_guess='{vision_data['best_guess']}' "
        f"labels={vision_data['labels'][:5]} "
        f"objects={vision_data['objects'][:3]} "
        f"logos={vision_data['logos']}"
    )

    context_parts = []
    if vision_data["best_guess"]:
        context_parts.append(f"Best guess label: {vision_data['best_guess']}")
    if vision_data["logos"]:
        context_parts.append(f"Detected brand/logo: {', '.join(vision_data['logos'])}")
    if vision_data["objects"]:
        context_parts.append(f"Detected objects: {', '.join(vision_data['objects'])}")
    if vision_data["labels"]:
        context_parts.append(f"Image labels: {', '.join(vision_data['labels'])}")
    if vision_data["web_entities"]:
        context_parts.append(f"Web context: {', '.join(vision_data['web_entities'])}")
    if vision_data["texts"]:
        context_parts.append(f"Visible text on product: {' | '.join(vision_data['texts'])}")

    vision_context  = "\n".join(context_parts)
    augmented_prompt = (
        f"Google Cloud Vision has already analyzed this image and found:\n"
        f"{vision_context}\n\n"
        f"Using these signals as your primary context, now:\n\n"
        f"{user_prompt}"
    )

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )
    image_part = {"inline_data": {"mime_type": mime_type, "data": b64_data}}
    response = model.generate_content(
        contents=[image_part, augmented_prompt],
        generation_config=genai.GenerationConfig(max_output_tokens=4000, temperature=0.2),
    )
    result = json.loads(_clean_json(response.text))
    result["vision_signals"] = vision_data   # attach raw signals for admin inspection
    return result


def _vision_ask(
    b64_data: str,
    mime_type: str,
    prompt: str,
    product_context: str,
    conversation_history: list,
) -> str:
    """Follow-up questions: Vision enriches context, Gemini answers."""
    try:
        vision_data   = _vision_detect(b64_data)
        context_parts = []
        if vision_data["best_guess"]:
            context_parts.append(f"Best guess: {vision_data['best_guess']}")
        if vision_data["logos"]:
            context_parts.append(f"Brand/logo: {', '.join(vision_data['logos'])}")
        if vision_data["objects"]:
            context_parts.append(f"Objects: {', '.join(vision_data['objects'])}")
        if vision_data["labels"]:
            context_parts.append(f"Labels: {', '.join(vision_data['labels'][:8])}")
        vision_context = "; ".join(context_parts)
    except Exception as e:
        print(f"[geminiSearch] ⚠️ Vision detection failed, falling back to image only: {e}")
        vision_context = ""

    system = (
        f"You are SnapSearch AI, an expert product analyst. "
        f"The user uploaded an image of: {product_context or 'a product'}. "
        + (f"Google Cloud Vision detected: {vision_context}. " if vision_context else "")
        + "Answer accurately, thoroughly, and helpfully. Use line breaks for readability."
    )

    model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=system)

    history = []
    for msg in conversation_history[-10:]:
        role = "model" if msg["role"] == "assistant" else "user"
        if isinstance(msg["content"], str):
            history.append({"role": role, "parts": [msg["content"]]})

    chat       = model.start_chat(history=history)
    image_part = {"inline_data": {"mime_type": mime_type, "data": b64_data}}
    response   = chat.send_message(
        [image_part, prompt],
        generation_config=genai.GenerationConfig(max_output_tokens=2000, temperature=0.4),
    )
    return response.text


# ─────────────────────────────────────────────────────────────────────────────
# Public API — these are what views.py calls
# ─────────────────────────────────────────────────────────────────────────────
def analyze_image_for_product(
    image_base64: str,
    query_type: str,
    provider: str = None,
) -> dict:
    """
    Analyze a product image and return structured JSON.

    Args:
        image_base64: full data URL ("data:image/png;base64,...") or raw base64
        query_type:   "buy" | "learn" | "others"
        provider:     "gemini" | "anthropic" | "vision" | None → uses DEFAULT_PROVIDER

    Returns dict with product info, or {"error": "...", "product_name": "Unknown Product"}
    """
    provider = (provider or DEFAULT_PROVIDER).lower()

    try:
        b64_data, mime_type = _parse_image_data(image_base64)
    except ValueError as e:
        print(f"[geminiSearch] ❌ Image parse error: {e}")
        return {
            "error": str(e),
            "product_name": "Unknown Product",
            "suppliers": [],
            "ai_provider": provider,
        }

    print(f"[geminiSearch] ✅ Analyzing — provider={provider}, mime={mime_type}, b64_len={len(b64_data)}")

    user_prompt = _get_user_prompt(query_type)

    try:
        if provider == "anthropic":
            result = _anthropic_analyze(b64_data, mime_type, user_prompt)
        elif provider == "vision":
            result = _vision_analyze(b64_data, mime_type, user_prompt)
        else:  # "gemini" or any unknown value
            result = _gemini_analyze(b64_data, mime_type, user_prompt)

        result["ai_provider"] = provider
        print(f"[geminiSearch] ✅ Success — product: {result.get('product_name')}")
        return result

    except json.JSONDecodeError as e:
        print(f"[geminiSearch] ❌ JSON parse error ({provider}): {e}")
        return {
            "error": f"JSON parse error: {e}",
            "product_name": "Unknown Product",
            "suppliers": [],
            "ai_provider": provider,
        }
    except Exception as e:
        print(f"[geminiSearch] ❌ API error ({provider}): {type(e).__name__}: {e}")
        return {
            "error": str(e),
            "product_name": "Unknown Product",
            "suppliers": [],
            "ai_provider": provider,
        }


def answer_product_question(
    prompt: str,
    product_context: str,
    image_base64: str,
    conversation_history: list,
    provider: str = None,
) -> str:
    """
    Answer a free-form question about a product with image context.

    Args:
        prompt:               user's question
        product_context:      product name/description for system context
        image_base64:         full data URL or raw base64
        conversation_history: list of {"role": "user"|"assistant", "content": "..."}
        provider:             "gemini" | "anthropic" | "vision" | None → DEFAULT_PROVIDER

    Returns answer string, or an error message string.
    """
    provider = (provider or DEFAULT_PROVIDER).lower()

    try:
        b64_data, mime_type = _parse_image_data(image_base64)
    except ValueError as e:
        print(f"[geminiSearch] ❌ Image parse error in ask: {e}")
        return f"Could not process the image: {str(e)}"

    try:
        if provider == "anthropic":
            return _anthropic_ask(b64_data, mime_type, prompt, product_context, conversation_history)
        elif provider == "vision":
            return _vision_ask(b64_data, mime_type, prompt, product_context, conversation_history)
        else:
            return _gemini_ask(b64_data, mime_type, prompt, product_context, conversation_history)
    except Exception as e:
        print(f"[geminiSearch] ❌ Ask error ({provider}): {type(e).__name__}: {e}")
        return f"Sorry, I couldn't process that question. Error: {str(e)}"