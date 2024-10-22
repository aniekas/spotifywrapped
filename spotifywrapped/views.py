import requests
import secrets
from django.shortcuts import render, redirect
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