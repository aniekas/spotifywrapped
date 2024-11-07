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
    top_artists = models.JSONField()  # Store as JSON data
    wrap_data = models.JSONField()    # Store as JSON data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Spotify Wrap for {self.user.user.username} - {self.year}"


# Signal to create a SpotifyUserProfile automatically when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        SpotifyUserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.spotifyuserprofile.save()
