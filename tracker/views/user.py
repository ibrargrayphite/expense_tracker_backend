from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from tracker.serializers.user import UserSerializer
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample,
    OpenApiResponse, inline_serializer
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers


# ── Inline response serializers for documentation ──────────────────────────

class _MessageSerializer(drf_serializers.Serializer):
    detail = drf_serializers.CharField()

class _UsernameErrorSerializer(drf_serializers.Serializer):
    username = drf_serializers.ListField(child=drf_serializers.CharField())
    suggestion = drf_serializers.CharField()

class _PasswordChangeSerializer(drf_serializers.Serializer):
    current_password = drf_serializers.CharField(
        help_text="The user's current password (required only when changing password)."
    )
    new_password = drf_serializers.CharField(
        help_text="The new password (min 8 chars, must pass Django password validators)."
    )

class _ForgotPasswordSerializer(drf_serializers.Serializer):
    email = drf_serializers.EmailField(help_text="Email address associated with the account.")

class _ResetPasswordSerializer(drf_serializers.Serializer):
    uid = drf_serializers.CharField(help_text="Base64-encoded user ID from the reset link.")
    token = drf_serializers.CharField(help_text="Password-reset token from the reset link.")
    new_password = drf_serializers.CharField(help_text="The new password to set.")


@extend_schema_view(
    list=extend_schema(
        tags=["Users"],
        summary="List all users (Admin only)",
        description="Returns a paginated list of all registered users. Requires admin privileges.",
        responses={200: UserSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Users"],
        summary="Retrieve a user (Admin only)",
        description="Returns detailed information for a specific user. Requires admin privileges.",
        responses={200: UserSerializer},
    ),
    update=extend_schema(
        tags=["Users"],
        summary="Update a user (Admin only)",
        description="Full update of a user record. Requires admin privileges.",
        responses={200: UserSerializer},
    ),
    partial_update=extend_schema(
        tags=["Users"],
        summary="Partial-update a user (Admin only)",
        description="Partial update of a user record. Requires admin privileges.",
        responses={200: UserSerializer},
    ),
    destroy=extend_schema(
        tags=["Users"],
        summary="Delete a user (Admin only)",
        description="Permanently deletes a user and all associated data. Requires admin privileges.",
        responses={204: None},
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    User management endpoints.

    list     GET    /api/users/          (Admin only)
    create   POST   /api/users/          (Public - Register)
    retrieve GET    /api/users/{id}/     (Admin only)
    update   PUT    /api/users/{id}/     (Admin only)
    partial  PATCH  /api/users/{id}/     (Admin only)
    destroy  DELETE /api/users/{id}/     (Admin only)

    Custom actions:
    - me          GET    /api/users/me/          (Get current user)
    - update_me   PATCH  /api/users/update_me/   (Update own profile)
    - forgot      POST   /api/users/forgot/      (Request password reset)
    - reset       POST   /api/users/reset/       (Perform password reset)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'forgot_password', 'reset_password']:
            permission_classes = [permissions.AllowAny]
        elif self.action == 'me':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @extend_schema(
        tags=["Auth"],
        summary="Register a new user",
        description=(
            "Creates a new user account. This endpoint is **public** (no authentication required).\n\n"
            "**Required fields:** `username`, `email`, `password`\n\n"
            "**Optional fields:** `first_name`, `last_name`\n\n"
            "If the chosen username is already taken, the API returns HTTP 400 with a "
            "suggested alternative username."
        ),
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(
                response=_UsernameErrorSerializer,
                description="Username already exists – includes a suggested alternative.",
                examples=[
                    OpenApiExample(
                        "Username taken",
                        value={"username": ["A user with that username already exists."], "suggestion": "johndoe123"},
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Register example",
                request_only=True,
                value={
                    "username": "johndoe",
                    "email": "john@example.com",
                    "password": "SecurePass123!",
                    "first_name": "John",
                    "last_name": "Doe",
                },
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        if User.objects.filter(username=username).exists():
            first_name = request.data.get('first_name', '').lower()
            last_name  = request.data.get('last_name', '').lower()
            import random, string
            base = f"{first_name}{last_name}" or "user"
            for _ in range(10):  # avoid infinite loop
                suggestion = base + ''.join(random.choices(string.digits, k=3))
                if not User.objects.filter(username=suggestion).exists():
                    break
            else:
                return Response(
                    {"detail": "Unable to generate username. Try again."},
                    status=400
                )
            return Response(
                {'username': ['A user with that username already exists.'], 'suggestion': suggestion},
                status=400,
            )
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Users"],
        summary="Get current user profile",
        description=(
            "Returns the full profile of the currently authenticated user, "
            "including their `phone_number` stored in `UserProfile`."
        ),
        responses={200: UserSerializer},
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Update current user profile",
        description=(
            "Allows the authenticated user to update their own profile.\n\n"
            "**Updatable fields:**\n"
            "- `first_name` *(string)* – First name\n"
            "- `last_name` *(string)* – Last name\n"
            "- `email` *(string)* – Email address\n"
            "- `phone_number` *(string)* – Phone number (stored in UserProfile)\n\n"
            "**Password change** (all three fields required together):\n"
            "- `current_password` *(string)* – Current password for verification\n"
            "- `new_password` *(string)* – The new password (must pass Django validators)\n\n"
            "You can update profile fields and change password in the same request."
        ),
        request=inline_serializer(
            name="UpdateMeRequest",
            fields={
                "first_name": drf_serializers.CharField(required=False),
                "last_name": drf_serializers.CharField(required=False),
                "email": drf_serializers.EmailField(required=False),
                "phone_number": drf_serializers.CharField(required=False, help_text="Stored in UserProfile."),
                "current_password": drf_serializers.CharField(required=False, help_text="Required if changing password."),
                "new_password": drf_serializers.CharField(required=False, help_text="Must meet Django password requirements."),
            }
        ),
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Validation error (e.g. wrong current password, weak new password).",
                examples=[
                    OpenApiExample("Wrong password", value={"current_password": "Current password is incorrect."}),
                    OpenApiExample("Weak password", value={"new_password": ["This password is too short."]}),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Update name & phone",
                request_only=True,
                value={"first_name": "John", "last_name": "Doe", "phone_number": "+923001234567"},
            ),
            OpenApiExample(
                "Change password",
                request_only=True,
                value={"current_password": "OldPass123!", "new_password": "NewSecurePass456!"},
            ),
        ],
    )
    @action(detail=False, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_me(self, request):
        """Allow authenticated user to update their own profile fields."""
        user = request.user
        data = request.data

        # Update basic User fields
        for field in ('first_name', 'last_name', 'email'):
            if field in data:
                setattr(user, field, data[field])

        # Update phone_number on UserProfile
        if 'phone_number' in data:
            from tracker.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = data['phone_number']
            profile.save()

        # Handle password change (requires current_password + new_password)
        new_password = data.get('new_password')
        if new_password:
            current_password = data.get('current_password')
            if not current_password:
                return Response(
                    {'current_password': 'Current password is required to set a new one.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not user.check_password(current_password):
                return Response(
                    {'current_password': 'Current password is incorrect.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                return Response({'new_password': e.messages}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)

        user.save()
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @extend_schema(
        tags=["Auth"],
        summary="Request a password reset link",
        description=(
            "Sends a password-reset email to the provided address if an account is found.\n\n"
            "The email contains a link to the frontend reset page with `uid` and `token` query params.\n\n"
            "This endpoint is **public** (no authentication required)."
        ),
        request=_ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Reset email sent successfully.",
                examples=[OpenApiExample("Success", value={"detail": "Password reset link sent to your email."})],
            ),
            400: OpenApiResponse(
                description="Email field missing.",
                examples=[OpenApiExample("Missing email", value={"detail": "Email is required."})],
            ),
            404: OpenApiResponse(
                description="No user found with that email.",
                examples=[OpenApiExample("Not found", value={"detail": "User not found."})],
            ),
        },
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
                
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            params = urlencode({'uid': uid, 'token': token})
            reset_url = f"{frontend_url}/reset-password?{params}"

            subject = "Reset Your XPENSE Password"
            html_content = f"""
                                <p>Hello,</p>
                                <p>Click the button below to reset your password:</p>
                                <p>
                                    <a href="{reset_url}" style="padding:10px 15px;background:#4f46e5;color:white;text-decoration:none;border-radius:5px;">
                                        Reset Password
                                    </a>
                                </p>
                                <p>If you didn't request this, you can ignore this email.</p>
                            """
            
            if SendGridAPIClient and getattr(settings, 'SENDGRID_API_KEY', None):
                email_message = Mail(
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_emails=email,
                    subject=subject,
                    html_content=html_content
                )
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                sg.client.mail.send.post(request_body=email_message.get())
            else:
                send_mail(
                    subject,
                    "Reset your password here: " + reset_url,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_content
                )

            return Response({"detail": "Password reset link sent to your email."})
        except Exception as e:
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=["Auth"],
        summary="Reset password using token",
        description=(
            "Validates the `uid` + `token` from the reset email and sets the new password.\n\n"
            "This endpoint is **public** (no authentication required).\n\n"
            "**Required fields:** `uid`, `token`, `new_password`"
        ),
        request=_ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successfully.",
                examples=[OpenApiExample("Success", value={"detail": "Password has been reset successfully."})],
            ),
            400: OpenApiResponse(
                description="Invalid/expired token or weak password.",
                examples=[
                    OpenApiExample("Invalid link", value={"detail": "Invalid or expired reset link."}),
                    OpenApiExample("Weak password", value={"detail": ["This password is too common."]}),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Reset password",
                request_only=True,
                value={"uid": "MQ", "token": "abc123-def456", "new_password": "NewSecurePass456!"},
            )
        ],
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uidb64, token, new_password]):
            return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password has been reset successfully."})
