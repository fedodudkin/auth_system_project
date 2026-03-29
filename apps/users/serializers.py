from rest_framework import serializers

from apps.users import services
from apps.users.models import User


class UserRegisterSerializer(serializers.Serializer):
    """Сериализатор для регистрации нового пользователя."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirmation = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        """Проверяем уникальность email."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        """Проверяем совпадение паролей."""
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "Пароли не совпадают."}
            )
        return attrs

    def create(self, validated_data: dict) -> User:
        """Создаём пользователя с хэшированным паролем."""
        validated_data.pop("password_confirmation")  # Не сохраняем в БД.
        user = User.objects.create(
            name=validated_data["name"],
            email=validated_data["email"],
            password_hash=services.hash_password(validated_data["password"]),
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для валидации учётных данных при входе."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].lower()
        password = attrs["password"]

        try:
            user = User.objects.select_related("role").get(email=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Неверный email или пароль.")

        if not services.verify_password(password, user.password_hash):
            raise serializers.ValidationError("Неверный email или пароль.")

        # Прокидываем объект пользователя дальше в view.
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения профиля пользователя."""

    role = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class UserUpdateSerializer(serializers.Serializer):
    """Сериализатор для частичного обновления профиля."""

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    def validate_email(self, value: str) -> str:
        value = value.lower()
        # Исключаем текущего пользователя из проверки уникальности.
        user: User = self.context["request"].my_user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError(
                "Этот email уже используется другим пользователем."
            )
        return value

    def update(self, instance: User, validated_data: dict) -> User:
        if "name" in validated_data:
            instance.name = validated_data["name"]
        if "email" in validated_data:
            instance.email = validated_data["email"]
        if "password" in validated_data:
            password_hash = services.hash_password(validated_data["password"])
            instance.password_hash = password_hash
        instance.save()
        return instance
