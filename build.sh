#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Populate public demo media from versioned source assets. Runtime uploads stay
# outside Git and should use managed object storage in production.
mkdir -p media/services/image media/doctors/images
cp -f services/image/* media/services/image/
cp -f doctors/images/* media/doctors/images/

python manage.py seed_demo
