from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect


from .forms import AuthenticationForm


class RaxLoginView(auth_views.LoginView):
    """Subclass of the built in login view with some minor changes."""
    authentication_form = AuthenticationForm

    def form_valid(self, form):
        """Security check complete. Log the user in.

        :param form: Authentication form with user inpur
        :type form: .forms.AuthenticationForm
        """
        user = form.get_user()
        auth_login(self.request, user)
        self.request.session['token'] = user.token
        self.request.session['user_id'] = user.id

        # Set the session expiration time to be the session timeout
        # from settings or the expiration of the token, whichever
        # occurs sooner.
        timeout = getattr(settings, 'SESSION_TIMEOUT', 3600)
        session_time = min(timeout, user.token_life)
        self.request.session.set_expiry(session_time)

        # Auth was success, redirect
        return HttpResponseRedirect(self.get_success_url())
