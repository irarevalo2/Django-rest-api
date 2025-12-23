from rest_framework import status
from rest_framework.response import Response

from rest_framework.views import APIView
from .models import User, MusicPrefs
from .serializers import UserSerializer, MusicPrefsSerializer
from .spotify_client import (
    SpotifyAuthError,
    get_artist_info,
    get_track_info,
    validate_tracks_batch,
    validate_artists_batch,
)


class UserListCreateView(APIView):
    def get(self, request):
        users = User.objects.all().order_by('id')
        data = [user.to_dictionary() for user in users]
        return Response({"data": data, "error": None}, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data, "error": None}, status=status.HTTP_201_CREATED)
        return Response({"data": None, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"data": None, "error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": user.to_dictionary(), "error": None}, status=status.HTTP_200_OK)
    
    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"data": None, "error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data, "error": None}, status=status.HTTP_200_OK)
        return Response({"data": None, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"data": None, "error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data, "error": None}, status=status.HTTP_200_OK)
        return Response({"data": None, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"data": None, "error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response({"data": True, "error": None}, status=status.HTTP_200_OK)

class UserMusicPrefsView(APIView):
    def get(self, request, user_id):
        try:
            prefs = MusicPrefs.objects.get(user_id=user_id)
            return Response({"data": prefs.to_dictionary(), "error": None}, status=status.HTTP_200_OK)
        except MusicPrefs.DoesNotExist:
            return Response({
                "data": {
                    "user_id": user_id,
                    "canciones_favoritas": [],
                    "artistas_favoritos": [],
                    "generos": [],
                },
                "error": None
            }, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        try:
            User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"data": None, "error": f"Usuario con id {user_id} no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        ids_canciones_favoritas = request.data.get("ids_canciones_favoritas", [])
        ids_artistas_favoritos = request.data.get("ids_artistas_favoritos", [])
        generos = request.data.get("generos", [])

        if not isinstance(ids_canciones_favoritas, list) or not isinstance(ids_artistas_favoritos, list):
            return Response(
                {"data": None, "error": "Los campos 'ids_canciones_favoritas' e 'ids_artistas_favoritos' deben ser una lista"},
                status=status.HTTP_400_BAD_REQUEST
            )

        def extract_ids(items):
            extracted = []
            for item in items:
                if isinstance(item, str):
                    extracted.append(item)
                elif isinstance(item, dict) and "id" in item:
                    extracted.append(item["id"])
            return extracted

        track_ids = extract_ids(ids_canciones_favoritas)
        artist_ids = extract_ids(ids_artistas_favoritos)

        warnings = {"invalid_track_ids": [], "invalid_artist_ids": []}

        try:
            valid_tracks = validate_tracks_batch(track_ids)
            valid_artists = validate_artists_batch(artist_ids)
        except SpotifyAuthError as exc:
            return Response({"data": None, "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response(
                {"data": None, "error": f"Error validando con Spotify: {str(exc)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        valid_track_ids = set(valid_tracks.keys())
        valid_artist_ids = set(valid_artists.keys())

        warnings["invalid_track_ids"] = [tid for tid in track_ids if tid not in valid_track_ids]
        warnings["invalid_artist_ids"] = [aid for aid in artist_ids if aid not in valid_artist_ids]

        validated_tracks = [valid_tracks[tid]["name"] for tid in track_ids if tid in valid_track_ids]
        validated_artists = [valid_artists[aid]["name"] for aid in artist_ids if aid in valid_artist_ids]

        try:
            prefs, created = MusicPrefs.objects.update_or_create(
                user_id=user_id,
                defaults={
                    "canciones_favoritas": validated_tracks,
                    "artistas_favoritos": validated_artists,
                    "generos": generos if isinstance(generos, list) else [],
                }
            )
            return Response({"data": prefs.to_dictionary(), "warnings": warnings, "error": None}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"data": None, "error": "Error guardando preferencias"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, user_id):
        try:
            prefs = MusicPrefs.objects.get(user_id=user_id)
            current = prefs.to_dictionary()
        except MusicPrefs.DoesNotExist:
            current = {
                "user_id": user_id,
                "canciones_favoritas": [],
                "artistas_favoritos": [],
                "generos": [],
            }

        merged = {**current, **request.data, "user_id": user_id}

        for key in ("canciones_favoritas", "artistas_favoritos", "generos"):
            if key in merged and not isinstance(merged[key], list):
                return Response(
                    {"data": None, "error": f"El campo '{key}' debe ser una lista"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        def extract_names(items):
            names = []
            for item in items:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict) and "name" in item:
                    names.append(item["name"])
            return names

        try:
            prefs, created = MusicPrefs.objects.update_or_create(
                user_id=user_id,
                defaults={
                    "canciones_favoritas": extract_names(merged.get("canciones_favoritas", [])),
                    "artistas_favoritos": extract_names(merged.get("artistas_favoritos", [])),
                    "generos": merged.get("generos", []),
                }
            )
            return Response({"data": prefs.to_dictionary(), "error": None}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"data": None, "error": "Error guardando preferencias"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SpotifyTrackInfoView(APIView):
    def get(self, request, track_id):
        try:
            info = get_track_info(track_id)
        except SpotifyAuthError as exc:
            return Response({"data": None, "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            return Response({"data": None, "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        
        if not info:
            return Response({"data": None, "error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": info, "error": None}, status=status.HTTP_200_OK)


class SpotifyArtistInfoView(APIView):
    def get(self, request, artist_id):
        try:
            info = get_artist_info(artist_id)
        except SpotifyAuthError as exc:
            return Response({"data": None, "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            return Response({"data": None, "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        
        if not info:
            return Response({"data": None, "error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": info, "error": None}, status=status.HTTP_200_OK)


def health_check(request):
    return Response({"status": "ok"})
