from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("video/", views.video,name='video'),
    path("video/<int:id>/",views.streaming,name="streaming")
]
