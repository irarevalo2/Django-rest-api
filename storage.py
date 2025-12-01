import json
import os
from typing import Any, Dict, List, Optional

import pymysql
import pymysql.cursors

# Variable global para la conexión MySQL
_mysql = None


def init_mysql(app) -> pymysql.Connection:
    """Inicializa la conexión MySQL con la aplicación Flask."""
    global _mysql
    host = os.getenv("MYSQL_HOST", "localhost")
    user = os.getenv("MYSQL_USER", "flaskuser")
    password = os.getenv("MYSQL_PASSWORD", "flaskpass")
    database = os.getenv("MYSQL_DATABASE", "flask_api_db")
    
    # Almacenar configuración en app.config para compatibilidad
    app.config["MYSQL_HOST"] = host
    app.config["MYSQL_USER"] = user
    app.config["MYSQL_PASSWORD"] = password
    app.config["MYSQL_DATABASE"] = database
    app.config["MYSQL_CURSORCLASS"] = "DictCursor"
    
    _mysql = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return _mysql


def _get_cursor():
    """Obtiene un cursor para ejecutar queries."""
    if _mysql is None:
        raise RuntimeError("MySQL no ha sido inicializado.")
    return _mysql.cursor()


def _execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Ejecuta una query SELECT y devuelve los resultados como lista de diccionarios."""
    cursor = _get_cursor()
    print("QUERY: " + query)
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    return results


def _execute_modify(query: str, params: tuple = None) -> int:
    """Ejecuta una query INSERT/UPDATE/DELETE y devuelve el número de filas afectadas."""
    cursor = _get_cursor()
    cursor.execute(query, params)
    _mysql.commit()
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


# Helpers para usuarios

def get_all_users() -> List[Dict[str, Any]]:
    """Obtiene todos los usuarios de la base de datos."""
    query = "SELECT id, nombre, email, edad, pais FROM users ORDER BY id"
    users = _execute_query(query)
    print(users)
    # Convertir resultados a formato esperado
    return [
        {
            "id": user["id"],
            "nombre": user["nombre"],
            "email": user["email"],
            "edad": user["edad"],
            "pais": user["pais"],
        }
        for user in users
    ]


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por su ID."""
    query = "SELECT id, nombre, email, edad, pais FROM users WHERE id = %s"
    results = _execute_query(query, (user_id,))
    if not results:
        return None
    user = results[0]
    return {
        "id": user["id"],
        "nombre": user["nombre"],
        "email": user["email"],
        "edad": user["edad"],
        "pais": user["pais"],
    }


def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo usuario y devuelve el usuario creado con su ID."""
    query = """
        INSERT INTO users (nombre, email, edad, pais)
        VALUES (%s, %s, %s, %s)
    """
    params = (
        user_data.get("nombre"),
        user_data.get("email"),
        user_data.get("edad"),
        user_data.get("pais"),
    )
    new_id = _execute_modify(query, params)
    return get_user_by_id(new_id)


def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza un usuario existente. Devuelve None si no existe."""
    # Verificar que el usuario existe
    if not get_user_by_id(user_id):
        return None
    
    query = """
        UPDATE users
        SET nombre = %s, email = %s, edad = %s, pais = %s
        WHERE id = %s
    """
    params = (
        user_data.get("nombre"),
        user_data.get("email"),
        user_data.get("edad"),
        user_data.get("pais"),
        user_id,
    )
    _execute_modify(query, params)
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    """Elimina un usuario. Devuelve True si se eliminó, False si no existía."""
    query = "DELETE FROM users WHERE id = %s"
    cursor = _get_cursor()
    cursor.execute(query, (user_id,))
    rows_affected = cursor.rowcount
    _mysql.commit()
    cursor.close()
    return rows_affected > 0

# Helpers para preferencias musicales

def get_music_prefs_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene las preferencias musicales de un usuario."""
    query = """
        SELECT id, user_id, canciones_favoritas, artistas_favoritos, generos
        FROM music_prefs
        WHERE user_id = %s
    """
    results = _execute_query(query, (user_id,))
    if not results:
        return None
    
    prefs = results[0]
    
    return {
        "user_id": prefs["user_id"],
        "canciones_favoritas": json.loads(prefs["canciones_favoritas"]) if prefs["canciones_favoritas"] else [],
        "artistas_favoritos": json.loads(prefs["artistas_favoritos"]) if prefs["artistas_favoritos"] else [],
        "generos": json.loads(prefs["generos"]) if prefs["generos"] else [],
    }


def upsert_music_prefs_for_user(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea o actualiza las preferencias musicales de un usuario.
    Usa INSERT ... ON DUPLICATE KEY UPDATE.
    """
    # Verificar que el usuario existe
    if not get_user_by_id(user_id):
        raise ValueError(f"Usuario con id {user_id} no existe")
    
    # Extraer solo los nombres de las canciones y artistas
    # Si vienen como objetos con "name", extraer solo el nombre
    # si vienen como strings, usarlos directamente
    def extract_names(items):
        """Extrae nombres de una lista que puede contener strings o objetos con 'name'."""
        names = []
        for item in items:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and "name" in item:
                names.append(item["name"])
        return names
    
    canciones_favoritas = extract_names(data.get("canciones_favoritas", []))
    artistas_favoritos = extract_names(data.get("artistas_favoritos", []))


    # Serializar las listas a JSON
    canciones_favoritas_json = json.dumps(canciones_favoritas)
    artistas_favoritos_json = json.dumps(artistas_favoritos)
    generos_json = json.dumps(data.get("generos", []))
    
    query = """
        INSERT INTO music_prefs (user_id, canciones_favoritas, artistas_favoritos, generos)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            canciones_favoritas = VALUES(canciones_favoritas),
            artistas_favoritos = VALUES(artistas_favoritos),
            generos = VALUES(generos)
    """
    params = (user_id, canciones_favoritas_json, artistas_favoritos_json, generos_json)
    _execute_modify(query, params)
    
    return get_music_prefs_by_user_id(user_id)

