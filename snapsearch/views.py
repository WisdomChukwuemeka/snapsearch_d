from rest_framework.views import APIView
from rest_framework.response import Response
from tokens.models import UserTokenBalance
from .models import SearchHistory
from .ai_service import analyze_image_for_product, answer_product_question


class AnalyzeImageView(APIView):
    def post(self, request):
        image_base64 = request.data.get("image_base64")
        query_type   = request.data.get("query_type", "buy")

        if not image_base64:
            return Response({"error": "No image provided"}, status=400)
        if query_type not in ("buy", "learn", "others"):
            return Response({"error": "Invalid query_type"}, status=400)

        balance, _ = UserTokenBalance.objects.get_or_create(
            user=request.user, defaults={"tokens": 0, "is_first_search": True}
        )
        if not balance.can_search():
            return Response({"error": "Insufficient tokens."}, status=402)

        result  = analyze_image_for_product(image_base64, query_type)
        was_free = balance.is_first_search
        balance.consume_tokens()

        SearchHistory.objects.create(
            user=request.user,
            product_name=result.get("product_name", "Unknown"),
            product_category=result.get("category", ""),
            query_type=query_type,
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

        if not prompt:
            return Response({"error": "No prompt provided"}, status=400)

        answer = answer_product_question(prompt, product_context, image_base64, conversation_history)
        return Response({"answer": answer})


class SearchHistoryView(APIView):
    def get(self, request):
        searches = SearchHistory.objects.filter(user=request.user)[:20]
        return Response({"searches": [
            {"product_name": s.product_name, "category": s.product_category,
             "query_type": s.query_type, "tokens_used": s.tokens_used,
             "was_free": s.was_free, "created_at": s.created_at.isoformat()}
            for s in searches
        ]})
