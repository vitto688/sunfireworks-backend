from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Role
from .serializers import (
    UserCreateSerializer,
    RoleSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    UserSerializer,
)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False)
    permission_classes = [IsAdminUser]
    serializer_class = UserCreateSerializer

    def get_queryset(self):
        # Get the requested view type from query parameters
        view_type = self.request.query_params.get('view', 'active')

        if view_type == 'all':
            # Return all users including deleted ones
            return User.objects.all()
        elif view_type == 'deleted':
            # Return only deleted users
            return User.objects.filter(is_deleted=True)
        else:
            # Default: return active (non-deleted) users
            return User.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.soft_delete()
        return Response(
            {'message': f'User {user.email} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'], url_path='restore')
    def restore_user(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk, is_deleted=True)
            user.is_deleted = False
            user.deleted_at = None
            user.is_active = True
            user.save()
            return Response(
                {'message': f'User {user.email} has been restored'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, email=email, password=password)

        if user and user.is_active and not user.is_deleted:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': 'Login successful'
            })
        elif user and user.is_deleted:
            return Response(
                {'error': 'This account has been deleted'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'message': 'Logout successful'})
            else:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                return Response({
                    'access': str(token.access_token)
                })
            else:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
