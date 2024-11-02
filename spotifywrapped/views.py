# spotifywrapped/views.py

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import SpotifyWrap
from django.contrib.auth import login
from django.contrib.auth.models import User


def authorize(request):
    """Redirect to Spotify for user authorization."""
    scope = "user-top-read user-read-recently-played"  # Define the necessary scopes
    auth_url = (
        "https://accounts.spotify.com/authorize?"
        f"client_id={settings.SPOTIFY_CLIENT_ID}&response_type=code&"
        f"redirect_uri={settings.SPOTIFY_REDIRECT_URI}&scope={scope}"
    )
    return redirect(auth_url)


def callback(request):
    """Handle Spotify's callback after user authorization."""
    code = request.GET.get("code")  # Get the authorization code
    token_url = "https://accounts.spotify.com/api/token"
    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "client_secret": settings.SPOTIFY_CLIENT_SECRET,
        },
    )

    tokens = response.json()
    access_token = tokens.get('access_token')

    # Here you could also obtain the refresh token and store it
    if access_token:
        user = request.user  # Assuming the user is authenticated
        save_wrap(user, access_token)  # Call to save the user's Spotify data

        # Use Spotify's user ID or email as username
        user_info = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': f'Bearer {access_token}'})
        user_data = user_info.json()

        spotify_user_id = user_data['id']  # Get Spotify user ID
        username = user_data['display_name'] or spotify_user_id  # Fallback to Spotify ID if no display name

        # Check if user already exists in your Django app
        user, created = User.objects.get_or_create(username=username, defaults={'first_name': username})

        if created:
            # Optionally save Spotify ID in a profile model or directly in User's extra fields
            pass  # Handle additional user setup if necessary

        login(request, user)  # Log the user in
        return redirect("wrap_list")  # Redirect to the user's wraps


@login_required
def wrap_list(request):
    """Display the user's saved Spotify wraps."""
    wraps = SpotifyWrap.objects.filter(user=request.user)
    return render(request, "app/wrap_list.html", {"wraps": wraps})


def save_wrap(user, token):
    """Fetch user's top tracks and save the wrap."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.spotify.com/v1/me/top/tracks", headers=headers)

    if response.status_code == 200:
        wrap_data = response.json()
        SpotifyWrap.objects.create(user=user, data=wrap_data)  # Save wrap data to the database
    else:
        print("Error fetching data from Spotify:", response.json())
