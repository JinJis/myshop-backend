from allauth.socialaccount.providers.oauth2.client import OAuth2Client


class CustomGoogleOAuth2Client(OAuth2Client):
    """
    Compatibility shim for dj-rest-auth SocialLoginSerializer.

    dj-rest-auth currently instantiates the client with a `scope` positional
    argument, but django-allauth's OAuth2Client does not accept it anymore.
    Accept the parameter and forward the remaining args to the base class to
    avoid the "multiple values for argument 'scope_delimiter'" TypeError.
    """

    def __init__(  # noqa: PLR0913
        self,
        request,
        consumer_key,
        consumer_secret,
        access_token_method,
        access_token_url,
        callback_url,
        _scope,  # This is fix for incompatibility between
        # django-allauth==65.3.1 and dj-rest-auth==7.0.1
        scope_delimiter=" ",
        headers=None,
        basic_auth=False,  # noqa: FBT002
    ):
        super().__init__(
            request,
            consumer_key,
            consumer_secret,
            access_token_method,
            access_token_url,
            callback_url,
            scope_delimiter,
            headers,
            basic_auth,
        )
