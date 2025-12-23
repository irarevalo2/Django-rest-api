from django.db import models


class User(models.Model):
    nombre = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    edad = models.IntegerField(null=True, blank=True)
    pais = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'users'

    def to_dictionary(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'edad': self.edad,
            'pais': self.pais,
        }


class MusicPrefs(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='music_prefs'
    )
    canciones_favoritas = models.JSONField(default=list)
    artistas_favoritos = models.JSONField(default=list)
    generos = models.JSONField(default=list)

    class Meta:
        db_table = 'music_prefs'

    def to_dictionary(self):
        return {
            'user_id': self.user_id,
            'canciones_favoritas': self.canciones_favoritas or [],
            'artistas_favoritos': self.artistas_favoritos or [],
            'generos': self.generos or [],
        }

