import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import SpotifyWrap, SpotifyUserProfile
from django.contrib.auth import login
from django.contrib.auth.models import User
import datetime
from django.http import HttpResponse


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
    """Handle Spotify's callback after user authorization and display error pages on failure."""
    code = request.GET.get("code")  # Get the authorization code

    if not code:
        return render(request, "accounts/error.html", {
            "message": "Authorization code not received from Spotify."
        }, status=400)

    # Step 1: Exchange code for access token
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

    if response.status_code != 200:
        error_data = response.json()
        error_description = error_data.get("error_description", "No error description provided.")
        expected_code = code  # This is the authorization code you received
        return render(request, "accounts/error.html", {
            "message": f"Spotify token request failed: {error_description}. Expected authorization code: {expected_code}. Actual error response: {error_data}"
        }, status=response.status_code)

    tokens = response.json()
    access_token = tokens.get("access_token")

    if not access_token:
        return render(request, "accounts/error.html", {
            "message": "Access token not received from Spotify."
        }, status=400)

    # Step 2: Fetch user info from Spotify
    user_info_response = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if user_info_response.status_code != 200:
        error_message = user_info_response.json().get("error", {}).get("message", "Failed to fetch user information.")
        return render(request, "accounts/error.html", {
            "message": f"Spotify user info request failed: {error_message}"
        }, status=user_info_response.status_code)

    user_data = user_info_response.json()
    spotify_user_id = user_data["id"]
    username = user_data.get("display_name") or spotify_user_id  # Fallback to Spotify ID if no display name is available

    # Step 3: Get or create the user in Django
    user, created = User.objects.get_or_create(username=username, defaults={"first_name": username})

    # Always create or update SpotifyUserProfile
    spotify_profile, created = SpotifyUserProfile.objects.get_or_create(
        user=user,
        defaults={
            'spotify_user_id': spotify_user_id,
            'access_token': access_token,
            'refresh_token': tokens.get("refresh_token", "")
        }
    )

    # Update existing profile with new tokens
    if not created:
        spotify_profile.access_token = access_token
        spotify_profile.refresh_token = tokens.get("refresh_token", "")
        spotify_profile.save()

    # Pass the SpotifyUserProfile instance to save_wrap
    try:
        save_wrap(spotify_profile, access_token)
    except Exception as e:
        return render(request, "accounts/error.html", {
            "message": f"Failed to save wrap data: {str(e)}"
        }, status=500)

    # Log the user in and redirect to wrap list page
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect("wrap_list")


def fetch_spotify_wrapped_metrics(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}

    # 1. Top 5 Genres
    top_tracks_url = 'https://api.spotify.com/v1/me/top/tracks'
    top_tracks_response = requests.get(top_tracks_url, headers=headers)
    top_tracks = top_tracks_response.json()['items'] if top_tracks_response.status_code == 200 else []

    # Extract artist IDs from top tracks to gather genres
    artist_ids = {artist['id'] for track in top_tracks for artist in track['artists']}
    genre_count = {}
    for artist_id in artist_ids:
        artist_url = f'https://api.spotify.com/v1/artists/{artist_id}'
        artist_response = requests.get(artist_url, headers=headers)
        if artist_response.status_code == 200:
            genres = artist_response.json().get('genres', [])
            for genre in genres:
                genre_count[genre] = genre_count.get(genre, 0) + 1
    top_5_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # 2. Total Minutes Listened
    recently_played_url = 'https://api.spotify.com/v1/me/player/recently-played'
    recent_tracks_response = requests.get(recently_played_url, headers=headers)
    recent_tracks = recent_tracks_response.json().get('items', [])
    total_minutes_listened = sum(track['track']['duration_ms'] / 60000 for track in recent_tracks)

    # 3. Top 5 Artists
    top_artists_url = 'https://api.spotify.com/v1/me/top/artists'
    top_artists_response = requests.get(top_artists_url, headers=headers)
    top_artists = top_artists_response.json()['items'][:5] if top_artists_response.status_code == 200 else []

    # 4. Number of Minutes Listened to Top Artist
    minutes_listened_to_top_artist = 0
    if top_artists:
        top_artist_id = top_artists[0]['id']
        minutes_listened_to_top_artist = sum(track['duration_ms'] / 60000 for track in top_tracks if top_artist_id in [artist['id'] for artist in track['artists']])

    # 5. Total Number of Artists Listened To
    total_artists_listened_to = len(artist_ids)

    # 6. Top 5 Albums
    album_count = {}
    for track in top_tracks:
        album = track['album']
        album_count[album['id']] = album_count.get(album['id'], 0) + 1
    top_5_albums = sorted(album_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # 7. Total Number of Albums Listened To
    total_albums_listened_to = len(album_count)

    # 8. Number of Times Top Album Was Played
    top_album_id = top_5_albums[0][0] if top_5_albums else None
    times_top_album_played = 0
    if top_album_id:
        times_top_album_played = sum(1 for track in top_tracks if track['album']['id'] == top_album_id)

    # 9. Top 10 Songs
    top_10_songs = top_tracks[:10]

    # 10. Number of Times Listened to Top Song
    top_song_id = top_tracks[0]['id'] if top_tracks else None
    times_listened_to_top_song = 0
    if top_song_id:
        times_listened_to_top_song = sum(1 for track in recent_tracks if track['track']['id'] == top_song_id)

    # Return all the metrics
    return {
        'top_5_genres': top_5_genres,
        'total_minutes_listened': total_minutes_listened,
        'top_5_artists': top_artists,
        'minutes_listened_to_top_artist': minutes_listened_to_top_artist,
        'total_artists_listened_to': total_artists_listened_to,
        'top_5_albums': top_5_albums,
        'total_albums_listened_to': total_albums_listened_to,
        'times_top_album_played': times_top_album_played,
        'top_10_songs': top_10_songs,
        'times_listened_to_top_song': times_listened_to_top_song
    }

@login_required
def wrap_list(request):
    """Display the user's saved Spotify wraps."""
    wraps = SpotifyWrap.objects.filter(user=request.user.spotifyuserprofile)  # Access through the profile
    return render(request, "spotify/top_tracks.html", {"wraps": wraps})


def save_wrap(user_profile, token):
    """Fetch user's top artists and wrap data, then save as a wrap for the specified year."""
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch top artists
    top_artists_response = requests.get("https://api.spotify.com/v1/me/top/artists", headers=headers)
    if top_artists_response.status_code != 200:
        print("Error fetching top artists from Spotify:", top_artists_response.json())
        return

    # Fetch top tracks or wrap data
    wrap_data_response = requests.get("https://api.spotify.com/v1/me/top/tracks", headers=headers)
    if wrap_data_response.status_code != 200:
        print("Error fetching wrap data from Spotify:", wrap_data_response.json())
        return

    # Parse the responses
    top_artists = top_artists_response.json()  # This will store the JSON data for top artists
    wrap_data = wrap_data_response.json()  # This will store the JSON data for top tracks/wrap

    # Set the year for the wrap; modify as needed
    year = datetime.datetime.now().year
 # or calculate dynamically based on the current date

    # Save the wrap data in the SpotifyWrap model
    SpotifyWrap.objects.create(
        user=user_profile,
        year=year,
        top_artists=top_artists,
        wrap_data=wrap_data
    )
