from django.urls import path

from .api.views import UserViewSet

user_view = UserViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    },
)

app_name = "users"

urlpatterns = [
    path("me/", user_view, name="user-me"),
]
