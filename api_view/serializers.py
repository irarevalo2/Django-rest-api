from rest_framework import serializers
from .models import User, MusicPrefs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nombre', 'email', 'edad', 'pais']


class MusicPrefsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicPrefs
        fields = ['user_id', 'canciones_favoritas', 'artistas_favoritos', 'generos']

