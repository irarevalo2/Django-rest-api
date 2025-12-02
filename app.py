from flask import Flask, jsonify, request

from spotify_client import (
    SpotifyAuthError,
    get_artist_info,
    get_track_info,
    validate_tracks_batch,
    validate_artists_batch,
)
from storage import (
    init_mysql,
    get_all_users,
    get_user_by_id,
    create_user as create_user_db,
    update_user as update_user_db,
    delete_user as delete_user_db,
    get_music_prefs_by_user_id,
    upsert_music_prefs_for_user,
)


def create_app():
    app = Flask(__name__)
    
    # Inicializar la conexión a MySQL al crear la aplicación
    init_mysql(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200


    # --- Manejo de errores ---

    @app.errorhandler(404)
    def handle_404(error):  
        return jsonify({"data": None, "error": "Not found"}), 404

    @app.errorhandler(400)
    def handle_400(error): 
        return jsonify({"data": None, "error": "Bad request"}), 400

    @app.errorhandler(500)
    def handle_500(error): 
        return jsonify({"data": None, "error": "Internal server error"}), 500

    # --- Rutas CRUD de usuarios ---

    @app.route("/users", methods=["GET"])
    def list_users():
        users = get_all_users()
        return jsonify({"data": users, "error": None}), 200

    @app.route("/users/<int:user_id>", methods=["GET"])
    def get_user(user_id: int):
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"data": None, "error": "Usuario no encontrado"}), 404
        return jsonify({"data": user, "error": None}), 200

    @app.route("/users", methods=["POST"])
    def create_user():
        payload = request.get_json() or {}
        nombre = payload.get("nombre")
        email = payload.get("email")

        if not nombre or not email:
            return (
                jsonify(
                    {
                        "data": None,
                        "error": "Campo 'nombre' y 'email' son requeridos",
                    }
                ),
                400,
            )

        try:
            new_user = create_user_db({
                "nombre": nombre,
                "email": email,
                "edad": payload.get("edad"),
                "pais": payload.get("pais"),
            })
            return jsonify({"data": new_user, "error": None}), 201
        except Exception as e:
            # Error de email duplicado u otros errores de BD
            error_msg = str(e)
            if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
                return jsonify({"data": None, "error": "El email ya esta en uso"}), 400
            return jsonify({"data": None, "error": "Error creando usuario"}), 500

    @app.route("/users/<int:user_id>", methods=["PUT"])
    def update_user(user_id: int):
        payload = request.get_json() or {}
        nombre = payload.get("nombre")
        email = payload.get("email")

        if not nombre or not email:
            return (
                jsonify(
                    {
                        "data": None,
                        "error": "Campo 'nombre' y 'email' son requeridos",
                    }
                ),
                400,
            )

        try:
            updated_user = update_user_db(user_id, {
                "nombre": nombre,
                "email": email,
                "edad": payload.get("edad"),
                "pais": payload.get("pais"),
            })
            if not updated_user:
                return jsonify({"data": None, "error": "Usuario no encontrado"}), 404
            return jsonify({"data": updated_user, "error": None}), 200
        except Exception as e:
            error_msg = str(e)
            if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
                return jsonify({"data": None, "error": "El email ya esta en uso"}), 400
            return jsonify({"data": None, "error": "Error actualizando usuario"}), 500

    @app.route("/users/<int:user_id>", methods=["PATCH"])
    def patch_user(user_id: int):
        payload = request.get_json() or {}
        current_user = get_user_by_id(user_id)
        
        if not current_user:
            return jsonify({"data": None, "error": "Usuario no encontrado"}), 404
        
        # Mezclar datos actuales con los nuevos usando ** para desempaquetar los diccionarios
        updated_data = {**current_user, **payload, "id": user_id}
        # Remover el id del payload para update_user_db
        updated_data.pop("id", None)
        
        try:
            updated_user = update_user_db(user_id, updated_data)
            if not updated_user:
                return jsonify({"data": None, "error": "Usuario no encontrado"}), 404
            return jsonify({"data": updated_user, "error": None}), 200
        except Exception as e:
            error_msg = str(e)
            if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
                return jsonify({"data": None, "error": "El email ya esta en uso"}), 400
            return jsonify({"data": None, "error": "Error actualizando usuario"}), 500

    @app.route("/users/<int:user_id>", methods=["DELETE"])
    def delete_user(user_id: int):
        deleted = delete_user_db(user_id)
        if not deleted:
            return jsonify({"data": None, "error": "Usuario no encontrado"}), 404
        
        return jsonify({"data": True, "error": None}), 200

    # --- Rutas de preferencias musicales ---

    @app.route("/users/<int:user_id>/music-prefs", methods=["GET"])
    def get_user_music_prefs(user_id: int):
        prefs = get_music_prefs_by_user_id(user_id)
        if not prefs:
            # Si no hay preferencias aún, devolvemos estructura vacía
            prefs = {
                "user_id": user_id,
                "canciones_favoritas": [],
                "artistas_favoritos": [],
                "generos": [], 
            }
        return jsonify({"data": prefs, "error": None}), 200

    @app.route("/users/<int:user_id>/music-prefs", methods=["PUT"])
    def put_user_music_prefs(user_id: int):
        payload = request.get_json() or {}

        # Extraer los arrays de IDs y géneros del payload
        ids_canciones_favoritas = payload.get("ids_canciones_favoritas", [])
        ids_artistas_favoritos = payload.get("ids_artistas_favoritos", [])
        generos = payload.get("generos", [])

        if not isinstance(ids_canciones_favoritas, list) or not isinstance(
            ids_artistas_favoritos, list
        ):
            return (
                jsonify(
                    {
                        "data": None,
                        "error": "Los campos 'ids_canciones_favoritas' e 'ids_artistas_favoritos' deben ser una lista",
                    }
                ),
                400,
            )

        # Extraer IDs: pueden venir como strings o como objetos con "id"
        def extract_ids(items):
            """Extrae IDs de una lista que puede contener strings o objetos con 'id'."""
            extracted = []
            for item in items:
                if isinstance(item, str):
                    # Si es un string, usarlo directamente como ID
                    extracted.append(item)
                elif isinstance(item, dict) and "id" in item:
                    # Si es un objeto con campo "id", extraer ese campo
                    extracted.append(item["id"])
            return extracted

        # Extraer los IDs limpios de canciones y artistas
        track_ids = extract_ids(ids_canciones_favoritas)
        artist_ids = extract_ids(ids_artistas_favoritos)

        # Validar IDs con Spotify
        warnings = {"invalid_track_ids": [], "invalid_artist_ids": []}
        
        try:
            # Obtener tracks y artistas validos
            valid_tracks = validate_tracks_batch(track_ids)
            valid_artists = validate_artists_batch(artist_ids)
        except SpotifyAuthError as exc:
            # Error de autenticación con Spotify (credenciales inválidas o faltantes)
            return jsonify({"data": None, "error": str(exc)}), 502
        except Exception as exc: 
            # Otros errores al comunicarse con Spotify 
            return jsonify({"data": None, "error": f"Error validando con Spotify: {str(exc)}"}), 502

        # Identificar IDs inválidos
        valid_track_ids = set(valid_tracks.keys())
        valid_artist_ids = set(valid_artists.keys())
        
        warnings["invalid_track_ids"] = [tid for tid in track_ids if tid not in valid_track_ids]
        warnings["invalid_artist_ids"] = [aid for aid in artist_ids if aid not in valid_artist_ids]

        # Extraer solo los nombres de los elementos validados
        validated_tracks = [valid_tracks[tid]["name"] for tid in track_ids if tid in valid_track_ids]
        validated_artists = [valid_artists[aid]["name"] for aid in artist_ids if aid in valid_artist_ids]

        # Preparar datos para guardar en la base de datos
        # Los géneros no se validan, se guardan tal cual
        prefs_data = {
            "canciones_favoritas": validated_tracks,
            "artistas_favoritos": validated_artists,
            "generos": generos if isinstance(generos, list) else [],
        }

        try:
            updated = upsert_music_prefs_for_user(user_id, prefs_data)
            response = {"data": updated, "warnings": warnings, "error": None}
            return jsonify(response), 200
        except ValueError as exc:
            # Error si el usuario no existe
            return jsonify({"data": None, "error": str(exc)}), 404
        except Exception as exc: 
            return jsonify({"data": None, "error": "Error guardando preferencias"}), 500

    @app.route("/users/<int:user_id>/music-prefs", methods=["PATCH"])
    def patch_user_music_prefs(user_id: int):
        payload = request.get_json() or {}
        current = get_music_prefs_by_user_id(user_id) or {
            "user_id": user_id,
            "canciones_favoritas": [],
            "artistas_favoritos": [],
            "generos": [],
        }

        # Mezclamos, pero asegurando que las listas sigan siendo listas
        merged = {**current, **payload, "user_id": user_id}

        for key in ("canciones_favoritas", "artistas_favoritos", "generos"):
            if key in merged and not isinstance(merged[key], list):
                return (
                    jsonify(
                        {
                            "data": None,
                            "error": f"EL campo '{key}' debe ser una lista",
                        }
                    ),
                    400,
                )

        updated = upsert_music_prefs_for_user(user_id, merged)
        return jsonify({"data": updated, "error": None}), 200

    # --- Integración con Spotify API ---
    # Endpoints que consultan información directamente desde Spotify

    @app.route("/spotify/tracks/<string:track_id>", methods=["GET"])
    def spotify_track_info(track_id: str):
        try:
            info = get_track_info(track_id)
        except SpotifyAuthError as exc:
            return jsonify({"data": None, "error": str(exc)}), 500
        except Exception as exc:
            return jsonify({"data": None, "error": str(exc)}), 502

        if not info:
            return jsonify({"data": None, "error": "Track not found"}), 404
        return jsonify({"data": info, "error": None}), 200

    @app.route("/spotify/artists/<string:artist_id>", methods=["GET"])
    def spotify_artist_info(artist_id: str):
        try:
            info = get_artist_info(artist_id)
        except SpotifyAuthError as exc:
            return jsonify({"data": None, "error": str(exc)}), 500
        except Exception as exc:
            return jsonify({"data": None, "error": str(exc)}), 502

        if not info:
            return jsonify({"data": None, "error": "Artist not found"}), 404
        return jsonify({"data": info, "error": None}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)


