-- MySQL crea la base de datos automáticamente según MYSQL_DATABASE en docker-compose.yml
USE flask_api_db;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    edad INT NULL,
    pais VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de preferencias musicales
CREATE TABLE IF NOT EXISTS music_prefs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    canciones_favoritas JSON,
    artistas_favoritos JSON,
    generos JSON,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Datos de prueba
INSERT INTO users (nombre, email, edad, pais) 
VALUES ('Ivan Arevalo', 'ivan_arevalo@example.com', 28, 'Colombia');

INSERT INTO music_prefs (user_id, canciones_favoritas, artistas_favoritos, generos) 
VALUES (1, '["Mr. Brightside"]', '["Foo Fighters"]', '["techno", "rock"]'); 