from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserTokenBalance, TokenPricing


class TokenBalanceView(APIView):
    def get(self, request):
        balance, _ = UserTokenBalance.objects.get_or_create(
            user=request.user, defaults={"tokens": 0, "is_first_search": True}
        )
        pricings = TokenPricing.objects.filter(is_active=True).order_by("price_naira")
        return Response({
            "tokens": balance.tokens,
            "is_first_search": balance.is_first_search,
            "total_searches": balance.total_searches,
            "pricing": [
                {
                    "id": p.id,
                    "tokens_per_pack": p.tokens_per_pack,
                    "price_naira": str(p.price_naira),
                    "label": p.label,
                }
                for p in pricings
            ],
        })