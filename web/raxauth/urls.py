from django.contrib.auth import views as auth_views
from django.urls import path

from .views import RaxLoginView

app_name = 'raxauth'
urlpatterns = [
    path(
        'login/',
        RaxLoginView.as_view(template_name='raxauth/login.html'),
        name='login'
    ),
    path('logout/', auth_views.logout_then_login, name='logout')
]
