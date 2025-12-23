from django.urls import path

from api_view import views

urlpatterns = [
    path('health', views.health_check, name='health_check'),
    path('users', views.UserListCreateView.as_view(), name='users_list_create'),
    path('users/<int:user_id>', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/music-prefs', views.UserMusicPrefsView.as_view(), name='user_music_prefs'),
    path('spotify/tracks/<str:track_id>', views.SpotifyTrackInfoView.as_view(), name='spotify_track_info'),
    path('spotify/artists/<str:artist_id>', views.SpotifyArtistInfoView.as_view(), name='spotify_artist_info'),
]
