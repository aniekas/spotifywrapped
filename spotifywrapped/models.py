from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class SpotifyUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    spotify_user_id = models.CharField(max_length=255, unique=True, default='', null=False)
    access_token = models.CharField(max_length=255, default="", null=False)
    refresh_token = models.CharField(max_length=255, default="", null=False)
    # Additional fields can be added here

    def __str__(self):
        return f"{self.user.username}'s Spotify Profile"

class SpotifyWrap(models.Model):
    user = models.ForeignKey(SpotifyUserProfile, on_delete=models.CASCADE, related_name='wraps')
    year = models.IntegerField()
    title = models.CharField(max_length=255, default="Spotify Wrap")
    top_artists = models.JSONField()  # Store as JSON data
    wrap_data = models.JSONField()    # Store as JSON data
    top_track_preview_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} for {self.user.user.username} - {self.year}"

# Signal to create a SpotifyUserProfile automatically when a User is created
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Get or create the SpotifyUserProfile
    profile, created = SpotifyUserProfile.objects.get_or_create(
        user=instance,
        defaults={"spotify_user_id": instance.username, "access_token": "", "refresh_token": ""}
    )
    if not created:
        # Optional: Update profile fields if necessary
        profile.spotify_user_id = profile.spotify_user_id or instance.username
        profile.save()

