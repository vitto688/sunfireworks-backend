from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Role

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'phone_number')

    def validate_email(self, value):
        # Prevent email updates
        if 'email' in self.initial_data:
            raise serializers.ValidationError("Email cannot be updated")
        return value

class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'role',
            'role_name',
            'phone_number',
            'is_active',
            'is_superuser',
            'is_deleted',
            'deleted_at',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('is_deleted', 'deleted_at', 'created_at', 'updated_at', 'email')

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'password',
            'role',
            'phone_number'
        )

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
