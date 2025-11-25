from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings

from myshop_backend.accounts.clients import CustomGoogleOAuth2Client


class GoogleLogin(
    SocialLoginView,
):  # if you want to use Authorization Code Grant, use this
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_OAUTH2_CALLBACK_URL
    client_class = CustomGoogleOAuth2Client
