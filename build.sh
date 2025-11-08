#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Pythonライブラリのインストール
pip install -r requirements.txt

# 2. Renderの環境に、Google Chromeのヘッドレスモード実行に必要な
#    システムライブラリをインストールする（apt-getの代わりに、Renderが用意したツールを使う）
apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    # -- 上記はChromeの実行に必要なライブラリ --
    # ここでChrome本体のインストールは行わず、Renderが提供するものを利用する