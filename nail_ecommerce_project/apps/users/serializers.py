from rest_framework import serializers
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, CustomerAddress


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = [
            'address_line1', 'address_line2', 'landmark',
            'city', 'state', 'pincode', 'use_for_home_service'
        ]

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label='Confirm password')

    # ✅ Registration API must accept these
    address_line1 = serializers.CharField(write_only=True, required=True)
    address_line2 = serializers.CharField(write_only=True, required=True)
    landmark = serializers.CharField(write_only=False, required=False, allow_blank=True)
    city = serializers.CharField(write_only=True, required=True)
    state = serializers.CharField(write_only=True, required=True)
    pincode = serializers.CharField(write_only=True, required=True)
    use_for_home_service = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'full_name', 'phone_number', 'role',
            'password', 'password2',
            # nested address fields
            'address_line1', 'address_line2', 'landmark', 'city', 'state', 'pincode', 'use_for_home_service'
        ]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        try:
            password_validation.validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return data

    def create(self, validated_data):
        # ✅ Extract password
        password = validated_data.pop('password')
        validated_data.pop('password2')

        # ✅ Extract address fields
        address_data = {
            'address_line1': validated_data.pop('address_line1'),
            'address_line2': validated_data.pop('address_line2'),
            'landmark': validated_data.pop('landmark', ''),
            'city': validated_data.pop('city'),
            'state': validated_data.pop('state'),
            'pincode': validated_data.pop('pincode'),
            'use_for_home_service': validated_data.pop('use_for_home_service', True),
        }

        # ✅ Create the user
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()

        # ✅ Link CustomerAddress
        CustomerAddress.objects.create(user=user, **address_data)

        return user


class UserSerializer(serializers.ModelSerializer):
    is_customer = serializers.ReadOnlyField()
    address = CustomerAddressSerializer(read_only=True)  # ✅ return full address details

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'full_name', 'role',
            'is_customer', 'is_active', 'is_staff', 'is_superuser',
            'address'
        ]
        read_only_fields = ['id', 'is_customer', 'is_staff', 'is_superuser', 'is_active']

    def update(self, instance, validated_data):
        # Prevent updating read-only fields
        for field in self.Meta.read_only_fields:
            validated_data.pop(field, None)
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['full_name'] = user.full_name
        token['username'] = user.username
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user_address = CustomerAddressSerializer(self.user.address).data if hasattr(self.user, "address") else None
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'full_name': self.user.full_name,
            'role': self.user.role,
            'address': user_address
        }
        return data