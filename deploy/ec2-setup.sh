#!/bin/bash
set -e

APP_DIR="/home/ubuntu/Spark"
cd "$APP_DIR"

python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

sudo cp deploy/schoolbridge.service /etc/systemd/system/schoolbridge.service
sudo systemctl daemon-reload
sudo systemctl enable schoolbridge
sudo systemctl restart schoolbridge
sudo systemctl status schoolbridge --no-pager
