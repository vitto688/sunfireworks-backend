from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, BasePermission
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Role
from .serializers import (
    UserCreateSerializer,
    UserUpdateSerializer,
    RoleSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    UserSerializer,
)

class IsSelfOrAdmin(BasePermission):
    """
    Custom permission to only allow users to edit their own information
    Admins can still list and create users, but can't modify other users
    """
    def has_permission(self, request, view):
        if view.action in ['list', 'create']:
            return request.user.is_staff
        return True

    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_superuser


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'change_password']:
            permission_classes = [IsAuthenticated, IsSelfOrAdmin]
        elif self.action == 'change_role':
            permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            permission_classes = [IsAuthenticated, IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        view_type = self.request.query_params.get('view', 'active')

        if view_type == 'all':
            return User.objects.all()
        elif view_type == 'deleted':
            return User.objects.filter(is_deleted=True)
        else:
            return User.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.soft_delete()
        return Response(
            {'message': f'User {user.email} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'error': 'Invalid old password'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {'message': 'Password updated successfully'},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], permission_classes=[IsAdminUser])
    def change_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role')

        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can change user roles'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
            return Response(
                {'message': f'Role updated to {role.name}'},
                status=status.HTTP_200_OK
            )
        except Role.DoesNotExist:
            return Response(
                {'error': 'Invalid role ID'},
                status=status.HTTP_400_BAD_REQUEST
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
