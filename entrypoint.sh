#!/bin/sh

# Aspetta che PostgreSQL sia pronto usando pg_isready
echo "Waiting for PostgreSQL..."
until pg_isready -h db -p 5432 -U gestionale_user; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up - executing command"

# Resto dello script...
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py populate_from_csv

exec "$@"
