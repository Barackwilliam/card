#!/usr/bin/env bash
# Hatua za kujenga kwenye hosting (mfano Render: Build Command = ./build.sh)
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
