from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from tracker.serializers.user import UserSerializer

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
    - me       GET    /api/users/me/       (Get current user)
    - forgot   POST   /api/users/forgot/   (Request password reset)
    - reset    POST   /api/users/reset/    (Perform password reset)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action in ['create', 'forgot_password', 'reset_password']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        if User.objects.filter(username=username).exists():
            first_name = request.data.get('first_name', '').lower()
            last_name  = request.data.get('last_name', '').lower()
            import random, string
            base = f"{first_name}{last_name}" or "user"
            while True:
                suggestion = base + ''.join(random.choices(string.digits, k=3))
                if not User.objects.filter(username=suggestion).exists():
                    break
            return __import__('rest_framework').response.Response(
                {'username': ['A user with that username already exists.'], 'suggestion': suggestion},
                status=400,
            )
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

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
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            subject = "Reset Your XPENSE Password"
            html_content = f"""
                                <p>Hello,</p>
                                <p>Click the button below to reset your password:</p>
                                <p>
                                    <a href="{reset_url}" style="padding:10px 15px;background:#4f46e5;color:white;text-decoration:none;border-radius:5px;">
                                        Reset Password
                                    </a>
                                </p>
                                <p>If you didn’t request this, you can ignore this email.</p>
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
            print(e)
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

