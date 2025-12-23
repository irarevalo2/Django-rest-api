import base64
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

TOKEN_URL = "https://accounts.spotify.com/api/token"
BASE_API_URL = "https://api.spotify.com/v1"

_ACCESS_TOKEN: Optional[str] = None
_ACCESS_TOKEN_EXPIRES_AT: float = 0.0


class SpotifyAuthError(Exception):
    pass


def _get_basic_auth_header() -> str:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise SpotifyAuthError(
            "SPOTIFY_CLIENT_ID o SPOTIFY_CLIENT_SECRET no están configurados"
        )
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")


def get_access_token() -> str:
    """Obtiene y cachea un token de acceso usando Client Credentials Flow."""
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRES_AT

    now = time.time()
    if _ACCESS_TOKEN and now < _ACCESS_TOKEN_EXPIRES_AT:
        return _ACCESS_TOKEN

    headers = {
        "Authorization": f"Basic {_get_basic_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=10)
    if resp.status_code != 200:
        raise SpotifyAuthError(
            f"Error obteniendo token de Spotify: {resp.status_code} {resp.text}"
        )

    payload = resp.json()
    _ACCESS_TOKEN = payload.get("access_token")
    expires_in = payload.get("expires_in", 3600)
    _ACCESS_TOKEN_EXPIRES_AT = now + expires_in - 30

    return _ACCESS_TOKEN or ""


def _auth_headers() -> Dict[str, str]:
    token = get_access_token()
    return {"Authorization": f"Bearer {token}"}


def get_track_info(spotify_track_id: str) -> Dict[str, Any]:
    url = f"{BASE_API_URL}/tracks/{spotify_track_id}"
    resp = requests.get(url, headers=_auth_headers(), timeout=10)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    data = resp.json()
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "duration_ms": data.get("duration_ms"),
        "explicit": data.get("explicit"),
        "preview_url": data.get("preview_url"),
        "album": {
            "id": data.get("album", {}).get("id"),
            "name": data.get("album", {}).get("name"),
        },
        "artists": [
            {
                "id": artist.get("id"),
                "name": artist.get("name"),
            }
            for artist in data.get("artists", [])
        ],
    }


def get_artist_info(spotify_artist_id: str) -> Dict[str, Any]:
    url = f"{BASE_API_URL}/artists/{spotify_artist_id}"
    resp = requests.get(url, headers=_auth_headers(), timeout=10)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    data = resp.json()
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "genres": data.get("genres", []),
        "popularity": data.get("popularity"),
        "followers": data.get("followers", {}).get("total"),
    }


def validate_tracks_batch(track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Valida múltiples IDs de tracks y retorna un diccionario con los válidos.
    Retorna {track_id: {"id": "...", "name": "..."}, ...}
    """
    valid_tracks = {}
    for track_id in track_ids:
        try:
            track_info = get_track_info(track_id)
            if track_info and track_info.get("id") and track_info.get("name"):
                valid_tracks[track_id] = {
                    "id": track_info["id"],
                    "name": track_info["name"],
                }
        except Exception:
            continue
    return valid_tracks


def validate_artists_batch(artist_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Valida múltiples IDs de artistas y retorna un diccionario con los válidos.
    Retorna {artist_id: {"id": "...", "name": "..."}, ...}
    """
    valid_artists = {}
    for artist_id in artist_ids:
        try:
            artist_info = get_artist_info(artist_id)
            if artist_info and artist_info.get("id") and artist_info.get("name"):
                valid_artists[artist_id] = {
                    "id": artist_info["id"],
                    "name": artist_info["name"],
                }
        except Exception:
            continue
    return valid_artists

