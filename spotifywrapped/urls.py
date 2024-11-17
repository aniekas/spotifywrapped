from django.urls import path, include
from . import views

urlpatterns = [
    path("login/", views.authorize, name="login"),  # URL to initiate Spotify authorization
    path("callback/", views.callback, name="callback"),  # URL for Spotify to redirect after authorization
    path("wraps/", views.wrap_list, name="wrap_list"),
    path("index/", views.index, name="index"),
    path('wraps/<int:wrap_id>/', views.wrap_detail, name='wrap_detail'),
    path("wrap/delete/<int:wrap_id>/", views.delete_wrap, name="delete_wrap"),
    path('contact/', views.contact, name='contact'),
    path('send_message/', views.send_message, name='send_message'),
    path("logout/", views.logout_view, name="logout"),
]
