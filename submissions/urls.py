from django.urls import path
from . import views

app_name = "submissions"

urlpatterns = [
    path("", views.submit_view, name="submit"),
    path("step2/", views.step2_view, name="step2"),
    path("step3/", views.step3_view, name="step3"),
    path("otp/", views.otp_view, name="otp"),
    path("success/", views.success_view, name="success"),
]
