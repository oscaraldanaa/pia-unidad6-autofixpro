#!/bin/bash
# Se ejecuta solo la primera vez que se crea el volumen de MySQL.
# Crea la base <MYSQL_DATABASE>_test y da permisos al usuario de la aplicación.
set -e
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}_test\` CHARACTER SET utf8mb4;
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}_test\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
