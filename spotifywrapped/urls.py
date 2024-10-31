from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('spotify/top-tracks/', views.get_top_tracks, name='top_tracks'),
    path('delete-account/', views.confirm_delete_account, name='confirm_delete_account'),
    path('delete-account/confirm/', views.delete_account, name='delete_account'),
    path('auth/login/spotify/', views.login_view, name='login'),  # Login view
    path('auth/complete/spotify/', views.index, name='index2'),  # Callback view
]
