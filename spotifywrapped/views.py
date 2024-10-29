import requests
import secrets
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import SpotifyWrap
from social_core.exceptions import AuthCanceled
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings


def index(request):
    return render(request, 'spotify/index.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('profile')
    return render(request, 'accounts/register.html')

def login_view(request):
    # Generate a random state value
    state_value = secrets.token_urlsafe(16)
    request.session['oauth_state'] = state_value

    # Redirect to Spotify authorization URL
    return redirect(f'https://accounts.spotify.com/authorize?'
                    f'client_id={settings.SPOTIFY_CLIENT_ID}&'
                    f'redirect_uri={settings.SOCIAL_AUTH_SPOTIFY_REDIRECT_URI}&'
                    f'state={state_value}&'
                    f'response_type=code&'
                    f'scope=user-top-read+playlist-read-private+user-library-read')
def password_reset_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return redirect('password_reset')
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been reset.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('password_reset')
    return render(request, 'accounts/password_reset.html')

def spotify_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')

    # Check if the state matches
    if state != request.session.get('oauth_state'):
        return HttpResponse("Invalid state parameter.", status=400)

    # Exchange the code for an access token
    token_url = 'https://accounts.spotify.com/api/token'
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SOCIAL_AUTH_SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }
    response = requests.post(token_url, data=data)
    token_info = response.json()

    if 'access_token' in token_info:
        access_token = token_info['access_token']

        # Fetch the user's top tracks
        wrap_data = fetch_spotify_wrap_data(access_token)

        # Get the current user
        user = request.user

        # Save the wrap data to the database
        SpotifyWrap.objects.create(user=user, wrap_data=wrap_data)

        return redirect('profile')
    else:
        raise AuthCanceled()  # Handle error case where token exchange fails

def fetch_spotify_wrap_data(access_token):
    url = 'https://api.spotify.com/v1/me/top/tracks'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()['items']
    else:
        return []  # Return an empty list if there's an error

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
def get_top_tracks(request):
    wraps = SpotifyWrap.objects.filter(user=request.user)
    return render(request, 'spotify/top_tracks.html', {'wraps': wraps})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def confirm_delete_account(request):
    if request.method == 'POST':
        return delete_account(request)
    return render(request, 'accounts/confirm_delete_account.html')

@login_required
def delete_account(request):
    user = request.user
    user.delete()  # Delete the user account
    return redirect('index')  # Redirect to a landing page or confirmation page

def contact_developers(request):
    return render(request, 'spotify/contact.html')