from rest_framework.views import APIView
from rest_framework.response import Response
from tokens.models import UserTokenBalance
from .models import GeminiSearchHistory
from .ai_service import analyze_image_for_product, answer_product_question, VALID_PROVIDERS


class AnalyzeImageView(APIView):
    def post(self, request):
        image_base64 = request.data.get("image_base64")
        query_type   = request.data.get("query_type", "buy")
        # Frontend can pass provider="gemini", "anthropic", or "vision"
        # If omitted, falls back to PREFERRED_AI_PROVIDER in settings.py
        provider     = request.data.get("provider", None)

        if not image_base64:
            return Response({"error": "No image provided"}, status=400)
        if query_type not in ("buy", "learn", "others"):
            return Response({"error": "Invalid query_type. Must be: buy | learn | others"}, status=400)
        if provider and provider not in VALID_PROVIDERS:
            return Response(
                {"error": f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}"},
                status=400,
            )

        # ── Token gate ───────────────────────────────────────────────────────
        balance, _ = UserTokenBalance.objects.get_or_create(
            user=request.user, defaults={"tokens": 0, "is_first_search": True}
        )
        if not balance.can_search():
            return Response({"error": "Insufficient tokens."}, status=402)

        # ── Call AI ──────────────────────────────────────────────────────────
        result = analyze_image_for_product(image_base64, query_type, provider=provider)

        # ✅ Only deduct tokens on success — never penalise API errors
        if "error" in result:
            print(f"[geminiSearch] AI error — tokens NOT deducted: {result['error']}")
            return Response(
                {"error": "AI service temporarily unavailable. Please try again shortly."},
                status=503,
            )

        was_free = balance.is_first_search
        balance.consume_tokens()

        GeminiSearchHistory.objects.create(
            user=request.user,
            product_name=result.get("product_name", "Unknown"),
            product_category=result.get("category", ""),
            query_type=query_type,
            ai_provider=result.get("ai_provider", "gemini"),
            tokens_used=0 if was_free else 2,
            was_free=was_free,
        )

        return Response(result)


class AskProductView(APIView):
    def post(self, request):
        prompt               = request.data.get("prompt", "").strip()
        product_context      = request.data.get("product_context", "")
        image_base64         = request.data.get("image_base64", "")
        conversation_history = request.data.get("conversation_history", [])
        provider             = request.data.get("provider", None)

        if not prompt:
            return Response({"error": "No prompt provided"}, status=400)
        if provider and provider not in VALID_PROVIDERS:
            return Response(
                {"error": f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}"},
                status=400,
            )

        answer = answer_product_question(
            prompt, product_context, image_base64, conversation_history, provider=provider
        )
        return Response({"answer": answer})


class SearchHistoryView(APIView):
    def get(self, request):
        searches = GeminiSearchHistory.objects.filter(user=request.user)[:20]
        return Response({"searches": [
            {
                "product_name": s.product_name,
                "category":     s.product_category,
                "query_type":   s.query_type,
                "ai_provider":  s.ai_provider,
                "tokens_used":  s.tokens_used,
                "was_free":     s.was_free,
                "created_at":   s.created_at.isoformat(),
            }
            for s in searches
        ]})


class ActiveProviderView(APIView):
    """
    GET /api/geminisearch/provider/
    Returns the active default provider + full list of available providers.
    """
    def get(self, request):
        from django.conf import settings
        provider = getattr(settings, "PREFERRED_AI_PROVIDER", "gemini")
        return Response({
            "active_provider": provider,
            "available":       list(VALID_PROVIDERS),
        })