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
from django.core.mail import send_mail
from django.http import JsonResponse

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
        wrap = save_wrap(user_profile, user_profile.access_token, timeframe)
        return redirect(reverse('wrap_detail', args=[wrap.id]))
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            wrap_data = response.json()

            # Create a title for the wrap based on timeframe
            timeframe_titles = {
                'long_term': 'All-Time',
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
                title=f"{title}"
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
    username = user_data.get(
        "display_name") or spotify_user_id  # Fallback to Spotify ID if no display name is available

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
    # try:
    #     save_wrap(spotify_profile, access_token)
    # except Exception as e:
    #     return render(request, "accounts/error.html", {
    #         "message": f"Failed to save wrap data: {str(e)}"
    #     }, status=500)

    # Log the user in and redirect to wrap list page
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect("index")


@login_required
def wrap_list(request):
    """Display the user's saved Spotify wraps."""
    wraps = SpotifyWrap.objects.filter(user=request.user.spotifyuserprofile)  # Access through the profile

    wrap_details = []  # This will store the calculated top track popularity and duration for each wrap

    for wrap in wraps:
        top_tracks = wrap.wrap_data.get("items", [])
        if top_tracks:
            top_track = top_tracks[0]
            top_track_name = top_track['name']
            top_track_popularity = top_track['popularity']

            # Calculate average track duration
            total_duration_ms = sum([track['duration_ms'] for track in top_tracks])
            avg_duration_min = round((total_duration_ms / len(top_tracks)) / 60000, 2) if top_tracks else 0
        else:
            top_track_name = "No top track available"
            top_track_popularity = "N/A"
            avg_duration_min = 0

        # Append wrap details including the calculated popularity and duration
        wrap_details.append({
            'wrap': wrap,
            'top_track_name': top_track_name,
            'top_track_popularity': top_track_popularity,
            'avg_duration_min': avg_duration_min
        })

    return render(request, "spotify/wrap_list.html", {
        "wraps": wraps,
        "wrap_details": wrap_details
        })


def save_wrap(user_profile, token, time_range="medium_term"):
    """Fetch user's top artists and tracks for a specific time range, then save as a wrap."""
    headers = {"Authorization": f"Bearer {token}"}
    valid_ranges = {"short_term", "medium_term", "long_term"}

    if time_range not in valid_ranges:
        time_range = "medium_term"  # Default to medium term if invalid time range is passed
    try:
        # Fetch top artists
        top_artists_response = requests.get(
            f"https://api.spotify.com/v1/me/top/artists?time_range={time_range}",
            headers=headers
        )
        top_artists_response.raise_for_status()
        top_artists = top_artists_response.json().get("items", [])  # Access the 'items' list for artists

        seen_artists = set()
        unique_top_artists = []
        for artist in top_artists:
            artist_name = artist.get("name")
            if artist_name not in seen_artists:
                unique_top_artists.append(artist)
                seen_artists.add(artist_name)
            if len(unique_top_artists) == 5:
                break
        
        # Fetch top tracks
        wrap_data_response = requests.get(
            f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}",
            headers=headers
        )
        wrap_data_response.raise_for_status()
        wrap_data = wrap_data_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Spotify API error: {e}")
        return  # Exit on API error
    # Determine wrap title
    title = {
        "short_term": "Last Month",
        "medium_term": "Last Year",
        "long_term": "All-Time"
    }.get(time_range, "Custom Wrap")
    # Extract a preview URL if available
    top_track_preview_url = next(
        (track.get("preview_url") for track in wrap_data.get("items", []) if track.get("preview_url")),
        None
    )

    # Save the wrap with the correct data
    return SpotifyWrap.objects.create(
        user=user_profile,
        year=datetime.datetime.now().year,
        title=title,
        top_artists=unique_top_artists,  # Store the list of top artists
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

    # Calculate the popularity of the top song
    top_tracks = wrap.wrap_data.get("items", [])
    if top_tracks:
        top_track = top_tracks[0]
        top_track_name = top_track['name']
        top_track_popularity = top_track['popularity']
    else:
        top_track_name = "No top track available"
        top_track_popularity = "N/A"
    
    # Calculate average track duration (example)
    total_duration_ms = sum([track['duration_ms'] for track in top_tracks])
    avg_duration_min = round((total_duration_ms / len(top_tracks)) / 60000, 2) if top_tracks else 0

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
        'top_track_name': top_track_name,  # Pass the top track name here
        'top_track_popularity': top_track_popularity,  # Pass the popularity value here
        'average_duration_min': avg_duration_min,
        'top_track_preview_url': top_track_preview_url,
        'top_track_title': top_track_title,
        'tracks_with_cover': tracks_with_cover,  # Pass the list of tracks with their cover images
    })


def top_song_popularity(top_tracks):
    if len(top_tracks) > 0:
        # Assuming you want the first song in the list as your "top song"
        top_song = top_tracks[0]

        # Extract the track name and popularity
        track_name = top_song['name']
        popularity = top_song['popularity']

        # Return both values as a tuple
        return track_name, popularity
    else:
        return None, 0

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
def contact(request):
    return render(request, 'spotify/contact.html')

def send_message(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        subject = f"Message from {name} ({email})"
        body = f"Message from {name} ({email}):\n\n{message}"
        recipient_list = ['arhea9@gatech.edu']  # Your email
        
        try:
            send_mail(subject, body, settings.EMAIL_HOST_USER, recipient_list, fail_silently=False)
        except Exception as e:
            return HttpResponse(f"Error sending email: {e}", status=500)

        return redirect('/app/contact')
    
    return HttpResponse('Invalid request method. Please use POST to send a message.', status=405)

def delete_all_wraps(request):
    """Delete all wraps associated with the current user."""
    SpotifyWrap.objects.all().delete()
    return render(request, 'spotify/index.html', {'message': 'All wraps have been deleted.'})

@login_required
def confirm_delete_account(request):
    return render(request, 'accounts/confirm_delete_account.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        print("POST")
        if request.user.is_authenticated:
            print("authenticated")
            # Delete Spotify wrap data
            SpotifyWrap.objects.filter(user=request.user.spotifyuserprofile).delete()
            print("deleted wrap")
            # Delete the user account
            request.user.delete()
            print("deleted user")
            # Log out the user
            logout(request)
            print("logged out")
            # Redirect to the account_deleted page
            return redirect('account_deleted')
        # Redirect back to index for non-POST requests
    return redirect('index')

def account_deleted(request):
    return render(request, 'accounts/account_deleted.html')

from django.http import JsonResponse

@login_required
def get_shareable_wrap_link(request, wrap_id):
    """Generate a shareable link for a user's Spotify Wrapped."""
    try:
        # Fetch the wrap for the current user
        wrap = SpotifyWrap.objects.get(id=wrap_id, user=request.user.spotifyuserprofile)

        # Generate the link to the wrap detail page
        shareable_link = request.build_absolute_uri(reverse('wrap_detail', args=[wrap_id]))

        return JsonResponse({"link": shareable_link}, status=200)
    except SpotifyWrap.DoesNotExist:
        return JsonResponse({"error": "Wrap not found."}, status=404)
