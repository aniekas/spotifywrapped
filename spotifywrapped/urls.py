from django.urls import path, include
from . import views
from .views import contact_developers

urlpatterns = [
    path("login/", views.authorize, name="login"),  # URL to initiate Spotify authorization
    path("callback/", views.callback, name="callback"),  # URL for Spotify to redirect after authorization
    path("wraps/", views.wrap_list, name="wrap_list"),
    path("index/", views.index, name="index"),
    path('wraps/<int:wrap_id>/', views.wrap_detail, name='wrap_detail'),

    path('logout/', views.spotify_logout, name='spotify_logout'),
    path('logout_complete/', views.logout_complete, name='logout_complete'),
    path("wrap/delete/<int:wrap_id>/", views.delete_wrap, name="delete_wrap"),
    path('contact/', contact_developers, name='contact_developers'),

    # path('confirm_delete_account/', views.confirm_delete_account, name='confirm_delete_account'),
    # path('delete_account/', views.delete_account, name='delete_account'),
    # path('account_deleted/', views.account_deleted, name='account_deleted'),  # Redirected page after deletion
]
