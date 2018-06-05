from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _


class AuthenticationForm(forms.Form):
    """Authentication form for authing through rackspace."""

    sso = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={'autofocus': True})
    )

    rsa = forms.CharField(
        max_length=32,
        strip=False,
        widget=forms.PasswordInput
    )

    error_messages = {
        'invalid_login': _(
            "Please enter a correct SSO and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        """Init the auth form."""
        self.user_cache = None
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        """Authenticate the user and save the result."""
        sso = self.cleaned_data.get('sso')
        rsa = self.cleaned_data.get('rsa')

        if sso is not None and rsa:
            # Cache the user if authentication is successful.
            self.user_cache = authenticate(self.request, sso=sso, rsa=rsa)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)

    def confirm_login_allowed(self, user):
        """Check the user ensuring the user is active.

        Raise validation error if user is not active.

        :param user: User to check
        :type user: RaxAuthUser
        """
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive'
            )

    def get_user_id(self):
        """Get id of user.

        :returns: Id of the user or None
        :rtype: str|None
        """
        if self.user_cache is not None:
            return self.user_cache.id
        return None

    def get_user(self):
        """Get the authenticated user.

        :returns: Authenticated user or None
        :rtype: RaxAuthUser|None
        """
        return self.user_cache
