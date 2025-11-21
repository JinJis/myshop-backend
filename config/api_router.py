from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from myshop_backend.api import urls as public_api_urls
from myshop_backend.users.api.views import UserViewSet

trailing_slash = "/?"
router = (
    DefaultRouter(trailing_slash=trailing_slash)
    if settings.DEBUG
    else SimpleRouter(trailing_slash=trailing_slash)
)

router.register("users", UserViewSet)


app_name = "api"
urlpatterns = router.urls + public_api_urls.urlpatterns
