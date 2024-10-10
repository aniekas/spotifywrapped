from django.contrib.auth.models import User
from django.db import models

class SpotifyWrap(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wrap_data = models.JSONField()  # Stores wrap data as JSON
    year = models.IntegerField()    # Spotify wrap year

    def __str__(self):
        return f"{self.user.username}'s Spotify Wrap for {self.year}"
from django.db import models

# Create your models here.
