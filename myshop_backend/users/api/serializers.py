from rest_framework import serializers

from myshop_backend.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
        ]
