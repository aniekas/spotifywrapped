<<<<<<< HEAD
# Generated by Django 5.1 on 2024-11-07 19:02
=======
# Generated by Django 5.1 on 2024-11-12 16:21
>>>>>>> e577892359b50251ab6ee93dad870ebbad353b3b

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
<<<<<<< HEAD
            name='SpotifyUserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_user_id', models.CharField(default='', max_length=255, unique=True)),
                ('access_token', models.CharField(default='', max_length=255)),
                ('refresh_token', models.CharField(default='', max_length=255)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SpotifyWrap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField()),
                ('top_artists', models.JSONField()),
                ('wrap_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wraps', to='spotifywrapped.spotifyuserprofile')),
=======
            name="SpotifyUserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "spotify_user_id",
                    models.CharField(default="", max_length=255, unique=True),
                ),
                ("access_token", models.CharField(default="", max_length=255)),
                ("refresh_token", models.CharField(default="", max_length=255)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SpotifyWrap",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("year", models.IntegerField()),
                ("title", models.CharField(default="Spotify Wrap", max_length=255)),
                ("top_artists", models.JSONField()),
                ("wrap_data", models.JSONField()),
                ("top_track_preview_url", models.URLField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("album_images", models.JSONField(default=list)),
                ("track_images", models.JSONField(default=list)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wraps",
                        to="spotifywrapped.spotifyuserprofile",
                    ),
                ),
>>>>>>> e577892359b50251ab6ee93dad870ebbad353b3b
            ],
        ),
    ]
