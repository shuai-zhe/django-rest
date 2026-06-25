#!/bin/bash

echo "Starting celery worker in background..."
celery -A analysis_app worker --loglevel=info &

sleep 2

echo "Starting celery beat in background..."
celery -A analysis_app beat --loglevel=info &

sleep 2

echo "Starting Django development server..."
python3 manage.py runserver