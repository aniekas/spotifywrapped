from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from .models import SpotifyWrap

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('profile')
    return render(request, 'accounts/register.html')

def login_view(request):
    # Standard login view logic
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def spotify_callback(request):
    # Spotify OAuth logic
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        scope="user-top-read"
    )

    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user = request.user
    wrap_data = fetch_spotify_wrap_data(sp)
    year = 2023  # Example year

    SpotifyWrap.objects.create(user=user, wrap_data=wrap_data, year=year)

    return redirect('profile')

def fetch_spotify_wrap_data(spotify):
    # Example function to fetch top tracks/artists from Spotify
    top_tracks = spotify.current_user_top_tracks(limit=10)
    return {'top_tracks': top_tracks}
from django.shortcuts import render

# Create your views here.
