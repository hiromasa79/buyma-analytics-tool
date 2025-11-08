#!/usr/bin/env bash
# exit on error
set -o errexit

# Poetryを使って、requirements.txtからライブラリをインストール
pip install -r requirements.txt

# Debian/UbuntuベースのRenderサーバーに、
# Google Chromeと、Seleniumが必要とするライブラリをインストール
apt-get update
apt-get install -y libnss3 libdbus-glib-1-2 libgtk-3-0 libxss1 libasound2
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb