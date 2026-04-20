import uuid
import requests
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.authentication import ClerkJWTAuthentication
from tokens.models import UserTokenBalance, TokenPricing
from .models import PaymentTransaction, Commission


def _get_email_from_request(request):
    """
    Safely resolve user email from multiple sources.
    Clerk JWT stores email in different claims depending on your Clerk config:
    - 'email' (custom claim)
    - 'email_addresses' (rare)
    - Falls back to user.email if synced, then a generated fallback.
    """
    payload = request.auth  # This is the decoded Clerk JWT dict
    email = None

    if isinstance(payload, dict):
        # Try common Clerk email claim locations
        email = (
            payload.get("email")
            or payload.get("email_address")
            or (payload.get("email_addresses") or [None])[0]
        )

    # Fallback: email stored on Django user object (set during get_or_create)
    if not email and request.user.email:
        email = request.user.email

    # Last resort fallback
    if not email:
        email = f"{request.user.username}@snapsearch.app"

    return email


@method_decorator(csrf_exempt, name="dispatch")
class InitiatePaymentView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pricing_id = request.data.get("pricing_id")

        # Try to fetch the specific pack the user selected
        if pricing_id:
            try:
                pricing = TokenPricing.objects.get(id=pricing_id, is_active=True)
            except TokenPricing.DoesNotExist:
                return Response({"error": "Invalid pricing pack selected."}, status=400)
        else:
            # Fall back to cheapest active pack
            pricing = TokenPricing.objects.filter(is_active=True).order_by("price_naira").first()

        if not pricing:
            # Absolute hardcoded fallback
            tokens, amount = 2, 200
        else:
            tokens = pricing.tokens_per_pack
            amount = pricing.price_naira

        reference = f"SNAP-{uuid.uuid4().hex[:16].upper()}"
        email = _get_email_from_request(request)

        try:
            PaymentTransaction.objects.create(
                user=request.user,
                reference=reference,
                amount_naira=amount,
                tokens_purchased=tokens,
                status="pending",
            )
        except Exception as e:
            return Response({"error": f"Could not create transaction record: {str(e)}"}, status=500)

        return Response({
            "reference": reference,
            "email": email,
            "amount_kobo": int(amount) * 100,
            "tokens": tokens,
        })
        

@method_decorator(csrf_exempt, name="dispatch")
class VerifyPaymentView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"success": False, "error": "No reference provided"}, status=400)

        try:
            txn = PaymentTransaction.objects.get(
                reference=reference, user=request.user, status="pending"
            )
        except PaymentTransaction.DoesNotExist:
            return Response(
                {"success": False, "error": "Transaction not found or already processed"},
                status=404,
            )

        # Verify with Paystack
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

        try:
            ps_response = requests.get(url, headers=headers, timeout=30)
            ps = ps_response.json()
        except requests.exceptions.Timeout:
            return Response({"success": False, "error": "Paystack verification timed out"}, status=504)
        except Exception as e:
            return Response({"success": False, "error": f"Paystack unreachable: {str(e)}"}, status=502)

        ps_data = ps.get("data", {})

        if ps.get("status") and ps_data.get("status") == "success":
            paid_kobo = ps_data.get("amount", 0)
            expected_kobo = int(float(txn.amount_naira) * 100)

            if paid_kobo < expected_kobo:
                txn.status = "failed"
                txn.paystack_response = ps
                txn.save()
                return Response(
                    {
                        "success": False,
                        "error": f"Amount mismatch. Expected ₦{txn.amount_naira}, got {paid_kobo / 100}",
                    },
                    status=400,
                )

            # Award tokens atomically
            balance, _ = UserTokenBalance.objects.get_or_create(
                user=request.user, defaults={"tokens": 0, "is_first_search": False}
            )
            balance.add_tokens(txn.tokens_purchased)

            # Persist Paystack metadata
            auth_data = ps_data.get("authorization", {})
            txn.status = "success"
            txn.paystack_reference = ps_data.get("reference", "")
            txn.channel = ps_data.get("channel", "")
            txn.card_last4 = auth_data.get("last4", "")
            txn.bank_name = auth_data.get("bank", "")
            txn.paystack_response = ps
            txn.completed_at = timezone.now()
            txn.save()

            return Response(
                {
                    "success": True,
                    "tokens_added": txn.tokens_purchased,
                    "new_balance": balance.tokens,
                }
            )

        else:
            txn.status = "failed"
            txn.paystack_response = ps
            txn.save()
            gateway_msg = ps_data.get("gateway_response", "Payment not successful")
            return Response({"success": False, "error": gateway_msg}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class TrackCommissionView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Commission.objects.create(
            user=request.user,
            platform=request.data.get("platform", ""),
            product_name=request.data.get("product_name", ""),
            affiliate_url=request.data.get("affiliate_url", ""),
            commission_pct=request.data.get("commission_pct", 5.00),
            estimated_usd=request.data.get("estimated_usd", 0),
        )
        return Response({"tracked": True})


@method_decorator(csrf_exempt, name="dispatch")
class TransactionHistoryView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        txns = PaymentTransaction.objects.filter(
            user=request.user, status="success"
        ).order_by("-initiated_at")[:20]

        return Response(
            {
                "transactions": [
                    {
                        "reference": t.reference,
                        "amount": str(t.amount_naira),
                        "tokens": t.tokens_purchased,
                        "channel": t.channel,
                        "bank": t.bank_name,
                        "date": t.initiated_at.isoformat(),
                    }
                    for t in txns
                ]
            }
        )