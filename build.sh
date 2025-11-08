#!/usr/bin/env bash
# exit on error
set -o errexit

# 必要なライブラリをインストール
pip install -r requirements.txt

# Playwrightの依存関係をインストール（これがChrome本体などをインストールしてくれる）
playwright install-deps
playwright install