import uuid
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.authentication import ClerkJWTAuthentication
from .models import UserTokenBalance, PaymentTransaction


class MeView(APIView):
    """Debug view — check your role and admin status."""
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username":     request.user.username,
            "email":        request.user.email,
            "is_staff":     request.user.is_staff,
            "is_superuser": request.user.is_superuser,
            "jwt_role":     request.auth.get("role") if isinstance(request.auth, dict) else None,
        })


class TokenBalanceView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance, _ = UserTokenBalance.objects.get_or_create(
            user=request.user,
            defaults={"tokens": 0, "is_first_search": True},
        )

        # ✅ Pull pricing from tokens app
        try:
            from tokens.models import TokenPricing
            pricings = TokenPricing.objects.filter(is_active=True).order_by("price_naira")
            pricing_data = [
                {
                    "id": p.id,
                    "tokens_per_pack": p.tokens_per_pack,
                    "price_naira": str(p.price_naira),
                    "label": p.label,
                }
                for p in pricings
            ]
        except Exception:
            pricing_data = []

        return Response({
            "tokens":          balance.tokens,
            "is_first_search": balance.is_first_search,
            "total_searches":  balance.total_searches,
            "pricing":         pricing_data,
        })


class InitiatePaymentView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pricing_id = request.data.get("pricing_id")

        # ✅ Use selected pack from tokens app
        try:
            from tokens.models import TokenPricing
            if pricing_id:
                pricing = TokenPricing.objects.get(id=pricing_id, is_active=True)
            else:
                pricing = TokenPricing.objects.filter(is_active=True).order_by("price_naira").first()

            if pricing:
                amount = pricing.price_naira
                tokens = pricing.tokens_per_pack
            else:
                amount, tokens = 200, 2
        except Exception:
            amount = request.data.get("amount", 200)
            tokens = request.data.get("tokens", 2)

        reference = f"SNAP-{uuid.uuid4().hex[:16].upper()}"

        # Get email safely
        email = request.user.email
        if not email and isinstance(request.auth, dict):
            email = request.auth.get("email", "")
        if not email:
            email = f"{request.user.username}@snapsearch.app"

        PaymentTransaction.objects.create(
            user=request.user,
            reference=reference,
            amount=amount,
            tokens_purchased=tokens,
            status="pending",
        )

        return Response({
            "reference":   reference,
            "email":       email,
            "amount_kobo": int(amount) * 100,
            "tokens":      tokens,
        })


class VerifyPaymentView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"success": False, "error": "No reference provided"}, status=400)

        try:
            transaction = PaymentTransaction.objects.get(
                reference=reference,
                user=request.user,
                status="pending",
            )
        except PaymentTransaction.DoesNotExist:
            return Response({"success": False, "error": "Transaction not found"}, status=404)

        paystack_url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

        try:
            ps_response = requests.get(paystack_url, headers=headers, timeout=30)
            ps_data = ps_response.json()
        except Exception:
            return Response({"success": False, "error": "Paystack verification failed"}, status=502)

        if ps_data.get("status") and ps_data["data"]["status"] == "success":
            paid_kobo    = ps_data["data"]["amount"]
            expected_kobo = int(float(transaction.amount)) * 100

            if paid_kobo < expected_kobo:
                transaction.status = "failed"
                transaction.paystack_response = ps_data
                transaction.save()
                return Response({"success": False, "error": "Amount mismatch"}, status=400)

            balance, _ = UserTokenBalance.objects.get_or_create(
                user=request.user,
                defaults={"tokens": 0, "is_first_search": False},
            )
            balance.add_tokens(transaction.tokens_purchased)

            transaction.status = "success"
            transaction.paystack_response = ps_data
            transaction.save()

            return Response({
                "success":      True,
                "tokens_added": transaction.tokens_purchased,
                "new_balance":  balance.tokens,
            })
        else:
            transaction.status = "failed"
            transaction.paystack_response = ps_data
            transaction.save()
            return Response({"success": False, "error": "Payment not successful"}, status=400)


class TransactionHistoryView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = PaymentTransaction.objects.filter(
            user=request.user
        ).order_by("-created_at")[:20]

        return Response({
            "transactions": [
                {
                    "reference": t.reference,
                    "amount":    str(t.amount),
                    "tokens":    t.tokens_purchased,
                    "status":    t.status,
                    "date":      t.created_at.isoformat(),
                }
                for t in transactions
            ]
        })