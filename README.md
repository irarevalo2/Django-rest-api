# Django-REST-API

API RESTful en Django para gestionar usuarios, sus preferencias musicales (almacenadas en MySQL) e integrar información básica de canciones y artistas desde la API oficial de Spotify.


## Tecnologías Utilizadas

- **Backend**: Django 4.2.8
- **Base de Datos**: MySQL 8.0
- **ORM/Driver**: mysqlclient 2.2.0
- **HTTP Client**: requests 2.32.3
- **Configuración**: python-dotenv 1.0.1
- **Contenedores**: Docker & Docker Compose
- **Python**: 3.11

## Estructura del Proyecto

```
Django-REST-API/
├── manage.py              # Script de gestión de Django
├── config/                # Proyecto Django (configuración)
│   ├── __init__.py
│   ├── settings.py        # Configuración de Django
│   └──  urls.py            # Rutas de la API
├── apiView/               # App principal de la API
│   ├── __init__.py
│   ├── models.py          # Modelos User y MusicPrefs
│   ├── views.py           # Vistas con JsonResponse
│   └── spotify_client.py  # Cliente para interactuar con la API de Spotify
├── init.sql               # Script de inicialización de la base de datos
├── requirements.txt       # Dependencias del proyecto
├── Dockerfile             # Configuración de la imagen Docker
├── docker-compose.yml     # Configuración de servicios Docker
└── README.md              # Este archivo
```

## Requisitos

- Docker y Docker Compose instalados
- Cuenta de desarrollador de Spotify para obtener credenciales de API

## Instalación y Ejecución con Docker

### 1. Configurar variables de entorno

Modifica el archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# MySQL Configuration
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=flask_api_db
MYSQL_USER=flaskuser
MYSQL_PASSWORD=flaskpass
MYSQL_PORT=3306

# Spotify API Configuration
SPOTIFY_CLIENT_ID=tu_client_id_aqui
SPOTIFY_CLIENT_SECRET=tu_client_secret_aqui
```

### 2. Construir y levantar los contenedores

```bash
docker-compose up -d
```

Esto construirá la imagen de la aplicación Django y levantará los servicios:
- **web**: Aplicación Django (puerto 5000)
- **db**: Base de datos MySQL 8.0 (puerto 3306)

### 3. Verificar que los servicios estén corriendo

```bash
docker-compose ps
```

### 4. Detener los servicios

```bash
docker-compose down
```

Para eliminar también los volúmenes (y por tanto los datos):

```bash
docker-compose down -v
```

## Estructura de la Base de Datos

### Tabla `users`
Almacena información de los usuarios.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK, AUTO_INCREMENT) | Identificador único del usuario |
| `nombre` | VARCHAR(285) NOT NULL | Nombre del usuario |
| `email` | VARCHAR(285) NOT NULL UNIQUE | Email del usuario (único) |
| `edad` | INT NULL | Edad del usuario (opcional) |
| `pais` | VARCHAR(285) NULL | País del usuario (opcional) |

### Tabla `music_prefs`
Almacena las preferencias musicales por usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK, AUTO_INCREMENT) | Identificador único de la preferencia |
| `user_id` | INT NOT NULL UNIQUE | ID del usuario (FK, ON DELETE CASCADE) |
| `canciones_favoritas` | JSON | Array JSON con nombres de canciones favoritas |
| `artistas_favoritos` | JSON | Array JSON con nombres de artistas favoritos |
| `generos` | JSON | Array JSON con géneros musicales preferidos |

**Nota**: Las preferencias se almacenan como nombres (strings) después de validar los IDs de Spotify. Solo se guardan las canciones y artistas válidos.

## API Endpoints

### Salud

#### `GET /health`
Comprueba que la API está funcionando.

**Respuesta exitosa:**
```json
{
  "status": "ok"
}
```


### CRUD de Usuarios

#### `GET /users`
Lista todos los usuarios registrados.

**Respuesta exitosa:**
```json
{
  "data": [
    {
      "id": 1,
      "nombre": "Ivan",
      "email": "ivan@example.com",
      "edad": 28,
      "pais": "Colombia"
    }
  ],
  "error": null
}
```

#### `GET /users/<id>`
Obtiene un usuario específico por su ID.

**Respuesta exitosa:**
```json
{
  "data": {
    "id": 1,
    "nombre": "ivan",
    "email": "ivan@example.com",
    "edad": 28,
    "pais": "Colombia"
  },
  "error": null
}
```

**Respuesta de error (404):**
```json
{
  "data": null,
  "error": "Usuario no encontrado"
}
```


#### `POST /users`
Crea un nuevo usuario.

**Campos requeridos:** `nombre`, `email`

**Campos opcionales:** `edad`, `pais`

**Body de ejemplo:**
```json
{
  "nombre": "Ivan",
  "email": "Ivan@example.com",
  "edad": 28,
  "pais": "Colombia"
}
```

**Respuesta exitosa (201):**
```json
{
  "data": {
    "id": 1,
    "nombre": "Ivan",
    "email": "Ivan@example.com",
    "edad": 28,
    "pais": "Colombia"
  },
  "error": null
}
```

#### `PUT /users/<id>`
Actualiza completamente un usuario existente (reemplaza todos los campos).

**Campos requeridos:** `nombre`, `email`

**Body de ejemplo:**
```json
{
  "nombre": "Ivan Arevalo",
  "email": "Ivan.arevalo@example.com",
  "edad": 26,
  "pais": "México"
}
```


#### `PATCH /users/<id>`
Actualiza parcialmente un usuario (solo los campos proporcionados).

**Body de ejemplo (solo actualizar edad):**
```json
{
  "edad": 27
}
```


#### `DELETE /users/<id>`
Elimina un usuario y sus preferencias musicales.

**Respuesta exitosa:**
```json
{
  "data": true,
  "error": null
}
```

---

### Preferencias Musicales

#### `GET /users/<id>/music-prefs`
Obtiene las preferencias musicales de un usuario.

**Respuesta exitosa:**
```json
{
  "data": {
    "user_id": 1,
    "canciones_favoritas": ["Mr. Brightside", "Bohemian Rhapsody"],
    "artistas_favoritos": ["Justin Timberlake", "The Beatles"],
    "generos": ["pop", "rock"]
  },
  "error": null
}
```

**Si el usuario no tiene preferencias:**
```json
{
  "data": {
    "user_id": 1,
    "canciones_favoritas": [],
    "artistas_favoritos": [],
    "generos": []
  },
  "error": null
}
```

#### `PUT /users/<id>/music-prefs`
Reemplaza completamente las preferencias musicales de un usuario. **Valida automáticamente los IDs de Spotify** antes de guardar.

**Características:**
- Valida todos los IDs de canciones y artistas con Spotify API
- Solo guarda los IDs válidos (ignora los inválidos)
- Devuelve warnings con los IDs inválidos encontrados
- Extrae los nombres de las canciones y artistas válidos desde Spotify
- Los géneros se guardan tal cual se proporcionan (sin validación)

**Body de ejemplo:**
```json
{
  "ids_canciones_favoritas": ["3n3Ppam7vgaVa1iaRUc9Lp", "invalid_id"],
  "ids_artistas_favoritos": ["1uNFoZAHBGtllmzznpCI3s"],
  "generos": ["pop", "rock"]
}
```

**Respuesta exitosa:**
```json
{
  "data": {
    "user_id": 1,
    "canciones_favoritas": ["Mr. Brightside"],
    "artistas_favoritos": ["Justin Timberlake"],
    "generos": ["pop", "rock"]
  },
  "warnings": {
    "invalid_track_ids": ["invalid_id"],
    "invalid_artist_ids": []
  },
  "error": null
}
```

#### `PATCH /users/<id>/music-prefs`
Actualiza parcialmente las preferencias musicales (mezcla con las existentes).

**Body de ejemplo (agregar una canción):**
```json
{
  "canciones_favoritas": ["Nueva Canción"]
}
```

---

### Integración con Spotify

#### `GET /spotify/tracks/<spotify_track_id>`
Obtiene información detallada de una canción desde Spotify.

**Respuesta exitosa:**
```json
{
  "data": {
    "id": "3n3Ppam7vgaVa1iaRUc9Lp",
    "name": "Mr. Brightside",
    "duration_ms": 222160,
    "explicit": false,
    "preview_url": "https://p.scdn.co/mp3-preview/...",
    "album": {
      "id": "0BTaCr7EFOg3qPXqfK8zNz",
      "name": "Hot Fuss"
    },
    "artists": [
      {
        "id": "0C0XlULifJtAgn6ZNCW2eu",
        "name": "The Killers"
      }
    ]
  },
  "error": null
}
```

**Respuesta de error (404):**
```json
{
  "data": null,
  "error": "Track not found"
}
```

#### `GET /spotify/artists/<spotify_artist_id>`
Obtiene información detallada de un artista desde Spotify.

**Respuesta exitosa:**
```json
{
  "data": {
    "id": "1uNFoZAHBGtllmzznpCI3s",
    "name": "Justin Timberlake",
    "genres": ["dance pop", "pop"],
    "popularity": 79,
    "followers": 8984220
  },
  "error": null
}
```

---

## Formato de Respuesta

Todas las respuestas de la API (excepto `/health`) siguen un formato JSON:

```json
{
  "data": ...,        // Datos de la respuesta (null en caso de error)
  "error": null | "mensaje de error",
  "warnings": {...}   // Opcional: presente en PUT /users/<id>/music-prefs
}
```

### Códigos de Estado HTTP

- `200 OK` - Operación exitosa
- `201 Created` - Recurso creado exitosamente
- `400 Bad Request` - Error en la petición (campos requeridos, validación, etc.)
- `404 Not Found` - Recurso no encontrado
- `500 Internal Server Error` - Error interno del servidor
- `502 Bad Gateway` - Error al comunicarse con Spotify API


## Persistencia de Datos

Los datos se persisten automáticamente en volúmenes de Docker. El volumen `mysql_data` almacena los datos de MySQL y persiste incluso si eliminas los contenedores (a menos que uses `docker-compose down -v`).
