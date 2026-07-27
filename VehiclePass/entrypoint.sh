#!/bin/bash
set -e

echo "=== Запуск инициализации контейнера BioPass Control ==="

echo "1. Применение миграций базы данных..."
python manage.py migrate --noinput

echo "2. Сбор статических файлов для WhiteNoise..."
python manage.py collectstatic --noinput

echo "3. Проверка и наполнение базы тестовыми аккаунтами..."
python create_dummy_data.py || true

echo "=== Система готова! Запуск веб-сервера ==="
exec "$@"
