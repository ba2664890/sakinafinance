#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Attente de la base de données..."

# On peut ajouter ici une boucle pour vérifier la connexion à Postgres si nécessaire,
# mais avec Neon (Serverless), la base est généralement disponible ou se "réveille" à la demande.

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Exécuter les commandes passées au conteneur (ex: gunicorn)
exec "$@"
