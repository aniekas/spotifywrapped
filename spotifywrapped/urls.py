from django.urls import path, include
from . import views
from django.urls import path
from .views import contact_developers



urlpatterns = [
    path('', views.index, name='index'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('login/', views.login_view, name='login'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('spotify/top-tracks/', views.get_top_tracks, name='top_tracks'),
    path('delete-account/', views.confirm_delete_account, name='confirm_delete_account'),
    path('delete-account/confirm/', views.delete_account, name='delete_account'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('contact/', contact_developers, name='contact_developers'),
]
