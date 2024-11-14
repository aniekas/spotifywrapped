import requests
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import SpotifyWrap, SpotifyUserProfile
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from datetime import timedelta
from django.http import HttpResponse

def home(request):
    """Render the home screen/welcome page."""
    return render(request, 'spotify/home.html')

from django.urls import reverse

def index(request):
    if request.method == 'POST':
        timeframe = request.POST.get('timeframe')
        user_profile = SpotifyUserProfile.objects.get(user=request.user)

        # Define endpoint URL based on timeframe
        url_map = {
            'long_term': 'https://api.spotify.com/v1/me/top/tracks?time_range=long_term',
            'medium_term': 'https://api.spotify.com/v1/me/top/tracks?time_range=medium_term',
            'short_term': 'https://api.spotify.com/v1/me/top/tracks?time_range=short_term'
        }
        url = url_map.get(timeframe)

        headers = {"Authorization": f"Bearer {user_profile.access_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            wrap_data = response.json()

            # Create a title for the wrap based on timeframe
            timeframe_titles = {
                'long_term': 'All-time',
                'medium_term': 'Last Year',
                'short_term': 'Last Month'
            }
            title = timeframe_titles.get(timeframe)

            # Save the wrap with the generated title
            wrap = SpotifyWrap.objects.create(
                user=user_profile,
                year=timezone.now().year,
                top_artists=wrap_data.get('items', []),
                wrap_data=wrap_data,
                title=f"{title} - {timezone.now().date()}"
            )

            # Redirect to the wrap_detail view for the new wrap
            return redirect(reverse('wrap_detail', args=[wrap.id]))
        else:
            # Handle error with Spotify API request
            return render(request, "accounts/error.html", {"message": "Failed to fetch data from Spotify"})

    return render(request, 'spotify/index.html')


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
            "message": f"Spotify user info request failed 200: {error_message}"
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
    return redirect("index")



@login_required
def wrap_list(request):
    """Display the user's saved Spotify wraps."""
    wraps = SpotifyWrap.objects.filter(user=request.user.spotifyuserprofile)  # Access through the profile
    return render(request, "spotify/wrap_list.html", {"wraps": wraps})


def save_wrap(user_profile, token, time_range="medium_term"):
    """Fetch user's top artists and tracks for a specific time range, then save as a wrap."""
    headers = {"Authorization": f"Bearer {token}"}
    valid_ranges = {"short_term", "medium_term", "long_term"}

    if time_range not in valid_ranges:
        time_range = "medium_term"  # Default to medium term if invalid time range is passed

    # Fetch top artists with specified time range
    top_artists_response = requests.get(
        f"https://api.spotify.com/v1/me/top/artists?time_range={time_range}",
        headers=headers
    )
    if top_artists_response.status_code != 200:
        print("Error fetching top artists from Spotify:", top_artists_response.json())
        return

    # Fetch top tracks with specified time range
    wrap_data_response = requests.get(
        f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}",
        headers=headers
    )
    if wrap_data_response.status_code != 200:
        print("Error fetching wrap data from Spotify:", wrap_data_response.json())
        return

    # Parse the responses
    top_artists = top_artists_response.json().get('items', [])
    wrap_data = wrap_data_response.json()

    # Set the wrap title based on the time range
    if time_range == "short_term":
        title = "Last Month"
    elif time_range == "medium_term":
        title = "Last 6 Months"
    else:
        title = "All Time"

    # Find the first track with an available preview URL
    top_track_preview_url = None
    for track in wrap_data.get("items", []):
        print(f"Track: {track['name']} - Preview URL: {track.get('preview_url')}")
        preview_url = track.get("preview_url")
        if preview_url:
            top_track_preview_url = preview_url
            break  # Exit the loop once a valid preview URL is found

    # Save the wrap data in the SpotifyWrap model
    SpotifyWrap.objects.create(
        user=user_profile,
        year=datetime.datetime.now().year,
        title=title,
        top_artists=top_artists,
        wrap_data=wrap_data,
        top_track_preview_url=top_track_preview_url  # Add a field for preview URL in your model
    )


def logout_view(request):
    """Log the user out and reset Spotify access token, then redirect to the home page."""
    # Optional: reset the user's Spotify access token upon logout
    if request.user.is_authenticated:
        spotify_profile = request.user.spotifyuserprofile
        spotify_profile.access_token = ""  # Clear the access token
        spotify_profile.save()

    logout(request)  # Log the user out
    print("User logged out")

    # Redirect to the home page (ensure this URL path exists in your urls.py)
    return redirect('home')


def wrap_detail(request, wrap_id):
    """Display detailed information for a specific Spotify wrap."""
    wrap = get_object_or_404(SpotifyWrap, id=wrap_id)
    top_track_preview_url = None
    top_track_title = None
    top_track_cover_url = None
    tracks_with_cover = []

    # Loop through the tracks and find the album cover for each one
    for track in wrap.wrap_data.get('items', []):
        if track.get('preview_url'):
            top_track_preview_url = track['preview_url']
            top_track_title = track['name']
            top_track_cover_url = track['album'].get('images', [{}])[0].get('url')

        # Add track and its album cover to the list
        album_cover_url = track['album'].get('images', [{}])[0].get('url')
        tracks_with_cover.append({
            'name': track['name'],
            'preview_url': track.get('preview_url'),
            'album_cover_url': album_cover_url
        })

    # Pass the tracks and cover URLs to the template
    return render(request, 'spotify/wrap_detail.html', {
        'wrap': wrap,
        'top_track_preview_url': top_track_preview_url,
        'top_track_title': top_track_title,
        'tracks_with_cover': tracks_with_cover,  # Pass the list of tracks with their cover images
    })


@login_required
def delete_wrap(request, wrap_id):
    """Delete a user's wrap."""
    # Get the SpotifyUserProfile associated with the current user
    user_profile = get_object_or_404(SpotifyUserProfile, user=request.user)

    # Fetch the wrap using the user_profile instance instead of request.user
    wrap = get_object_or_404(SpotifyWrap, id=wrap_id, user=user_profile)

    # Check if the wrap truly belongs to the user
    if wrap.user != user_profile:
        return HttpResponseForbidden("You are not allowed to delete this wrap.")

    # Delete the wrap and redirect
    wrap.delete()
    return redirect("wrap_list")