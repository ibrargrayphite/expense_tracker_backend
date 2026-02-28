from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers
from tracker.views import UserViewSet


# ── Documented JWT views ───────────────────────────────────────────────────

class _TokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        tags=["Auth"],
        summary="Login – obtain JWT token pair",
        description=(
            "Authenticates the user with their `username` and `password` and returns "
            "a short-lived **access token** (60 min) and a longer-lived **refresh token** (1 day).\n\n"
            "Include the access token in the `Authorization` header for all protected endpoints:\n"
            "```\nAuthorization: Bearer <access_token>\n```"
        ),
        request=inline_serializer(
            name="LoginRequest",
            fields={
                "username": drf_serializers.CharField(help_text="Your registered username."),
                "password": drf_serializers.CharField(help_text="Your password."),
            }
        ),
        responses={
            200: inline_serializer(
                name="TokenPairResponse",
                fields={
                    "access": drf_serializers.CharField(help_text="Short-lived JWT access token (60 minutes)."),
                    "refresh": drf_serializers.CharField(help_text="Long-lived JWT refresh token (1 day)."),
                }
            ),
            401: OpenApiResponse(
                description="Invalid credentials.",
                examples=[OpenApiExample("Bad credentials", value={"detail": "No active account found with the given credentials."})],
            ),
        },
        examples=[
            OpenApiExample(
                "Login example",
                request_only=True,
                value={"username": "johndoe", "password": "SecurePass123!"},
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class _TokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Auth"],
        summary="Refresh JWT access token",
        description=(
            "Uses a valid **refresh token** to issue a new **access token**.\n\n"
            "Since `ROTATE_REFRESH_TOKENS=True`, this also returns a new refresh token "
            "and invalidates the old one."
        ),
        request=inline_serializer(
            name="TokenRefreshRequest",
            fields={
                "refresh": drf_serializers.CharField(help_text="The refresh token obtained during login."),
            }
        ),
        responses={
            200: inline_serializer(
                name="TokenRefreshResponse",
                fields={
                    "access": drf_serializers.CharField(help_text="New access token (60 minutes)."),
                    "refresh": drf_serializers.CharField(help_text="New refresh token (replaces the old one)."),
                }
            ),
            401: OpenApiResponse(
                description="Refresh token invalid or expired.",
                examples=[OpenApiExample("Expired token", value={"detail": "Token is invalid or expired.", "code": "token_not_valid"})],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tracker.urls')),
    path('api/register/', UserViewSet.as_view({'post': 'create'}), name='register'),
    path('api/token/', _TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', _TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
