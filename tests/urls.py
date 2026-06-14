from django.http import HttpResponse
from django.urls import include, path


def login_view(request):
    return HttpResponse("login page")


urlpatterns = [
    path("accounts/login/", login_view, name="login"),
    path("verification/", include("verify_email.urls")),
]
