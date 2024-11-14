from django.urls import path, include
from . import views

urlpatterns = [
    path("login/", views.authorize, name="login"),  # URL to initiate Spotify authorization
    path("callback/", views.callback, name="callback"),  # URL for Spotify to redirect after authorization
    path("wraps/", views.wrap_list, name="wrap_list"),
    path("index/", views.index, name="index"),
    path('wraps/<int:wrap_id>/', views.wrap_detail, name='wrap_detail'),
    # path('logout/', views.spotify_logout, name="logout"),
    # path('logout/', views.spotify_logout, name='spotify_logout'),
    #     path('logout_complete/', views.logout_complete, name='logout_complete'),
]