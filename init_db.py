# init_db.py

import sqlite3

# 'database.db' という名前のデータベースファイルに接続（なければ新規作成）
connection = sqlite3.connect('database.db')

# データベースを操作するためのカーソルを作成
cursor = connection.cursor()

# usersテーブルを作成するSQL文
# id: ユーザーを識別するユニークな番号
# username: ユーザー名（ユニークでなければならない）
# password_hash: パスワードを安全に保存するためのハッシュ値
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
''')

print("データベースとusersテーブルの準備が完了しました。")

# 変更を確定
connection.commit()
# 接続を閉じる
connection.close()