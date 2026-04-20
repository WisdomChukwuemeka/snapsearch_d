import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class ClerkJWTAuthentication(BaseAuthentication):

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth_header = (
            request.headers.get("Authorization")
            or request.META.get("HTTP_AUTHORIZATION", "")
        )

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = self._verify_clerk_token(token)
        except Exception as e:
            print(f"🛑 CLERK AUTH ERROR: {e}")
            raise AuthenticationFailed(f"Invalid Clerk token: {str(e)}")

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise AuthenticationFailed("Token missing subject claim")

        email = (
            payload.get("email")
            or payload.get("email_address")
            or ""
        )

        user, created = User.objects.get_or_create(
            username=clerk_user_id,
            defaults={
                "email": email,
                "first_name": payload.get("given_name", ""),
                "last_name": payload.get("family_name", ""),
            },
        )

        # Sync email if changed
        if not created and email and user.email != email:
            user.email = email

        # ✅ Role from Clerk publicMetadata via JWT claim
        role = payload.get("role", "")
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
            print(f"✅ Admin granted: {clerk_user_id}")
        else:
            # ✅ NEVER downgrade an existing admin
            if not user.is_staff:
                user.is_staff = False
                user.is_superuser = False

        user.save()

        if created:
            # Use whichever token balance model your project uses
            try:
                from tokens.models import UserTokenBalance
                UserTokenBalance.objects.get_or_create(
                    user=user,
                    defaults={"tokens": 0, "is_first_search": True},
                )
            except Exception:
                from .models import UserTokenBalance
                UserTokenBalance.objects.get_or_create(
                    user=user,
                    defaults={"tokens": 0, "is_first_search": True},
                )

        print(f"✅ Auth: {clerk_user_id} | staff={user.is_staff} | role={role}")
        return (user, payload)

    def _verify_clerk_token(self, token):
        jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )