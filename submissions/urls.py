from django.urls import path
from . import views

app_name = "submissions"

urlpatterns = [
    path("",        views.login_view,   name="login"),
    path("otp/",    views.otp_view,     name="otp"),
    path("success/",views.success_view, name="success"),
]
