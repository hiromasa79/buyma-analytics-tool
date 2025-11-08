# app.py (一時ファイル利用・最終完成版)

from flask import Flask, render_template, request, session, redirect, url_for, g, flash, make_response
from scraper import analyze_buyma
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import functools
import pandas as pd
import io
import csv
import numpy as np
import json
import os
from datetime import date
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_12345'
DATABASE = 'database.db'
TEMP_FILE_PATH = os.path.join(os.path.dirname(__file__), 'temp_data.json')

# --- データベース接続のヘルパー ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- ログイン状態をチェックするデコレーター ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('このページにアクセスするにはログインが必要です。', 'info')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

# --- 各ページのルーティング ---

@app.route('/')
def index():
    if g.user:
        return redirect(url_for('tool'))
    return render_template('home.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        if not username or not password:
            error = 'ユーザー名とパスワードは必須です。'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"ユーザー名 '{username}' は既に使用されています。"
        if error is None:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       (username, generate_password_hash(password)))
            db.commit()
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('login'))
        flash(error, 'error')
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            error = 'ユーザー名またはパスワードが正しくありません。'
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('tool'))
        flash(error, 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。', 'success')
    return redirect(url_for('index'))

@app.route('/tool', methods=('GET', 'POST'))
@login_required 
def tool():
    if request.method == 'POST':
        buyma_url = request.form['buyma_url']
        
        period_type = request.form.get('period_type')
        if period_type == 'simple':
            period_months = int(request.form.get('period', 3))
            today = date.today()
            end_date = today + relativedelta(day=31)
            start_date = today + relativedelta(months=-(period_months - 1), day=1)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

        results = analyze_buyma(buyma_url, start_date_str, end_date_str)
        
        if results:
            df = pd.DataFrame(results)
            df['価格'] = pd.to_numeric(df['価格'].astype(str).replace('[¥,]', '', regex=True), errors='coerce').fillna(0)
            df['出品日'] = pd.to_datetime(df['出品日'], errors='coerce')
            df['成約日'] = pd.to_datetime(df['成約日'], errors='coerce')
            df.dropna(subset=['出品日', '成約日'], inplace=True)
            if not df.empty:
                df['取引日数'] = (df['成約日'] - df['出品日']).dt.days
                df = df[df['取引日数'] >= 0]
            if not df.empty:
                total_sales = df['価格'].sum()
                total_items = len(df)
                average_price = df['価格'].mean() if total_items > 0 else 0
                df['成約月'] = df['成約日'].dt.strftime('%Y-%m')
                brand_monthly_sales = df.groupby(['ブランド名', '成約月'])['価格'].sum().unstack(fill_value=0)
                chart_labels = brand_monthly_sales.columns.tolist()
                chart_datasets = []
                colors = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)']
                for i, (brand, sales_data) in enumerate(brand_monthly_sales.iterrows()):
                    chart_datasets.append({
                        'label': brand,
                        'data': sales_data.tolist(),
                        'backgroundColor': colors[i % len(colors)]
                    })
                category_counts = df['大カテゴリ'].value_counts()
                dashboard_data_dict = {
                    'summary': {'total_sales': f"¥{total_sales:,.0f}", 'total_items': total_items, 'average_price': f"¥{average_price:,.0f}"},
                    'brand_sales_chart': {'labels': chart_labels, 'datasets': chart_datasets},
                    'category_chart': {'labels': category_counts.index.tolist(), 'data': category_counts.values.tolist()}
                }
                
                temp_data = {
                    "results": results,
                    "dashboard_data_json": json.dumps(dashboard_data_dict)
                }
                with open(TEMP_FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(temp_data, f, ensure_ascii=False, indent=4)
            else:
                if os.path.exists(TEMP_FILE_PATH): os.remove(TEMP_FILE_PATH)
        else:
            if os.path.exists(TEMP_FILE_PATH): os.remove(TEMP_FILE_PATH)

        return redirect(url_for('tool'))

    results = None
    dashboard_data_json = None
    if os.path.exists(TEMP_FILE_PATH):
        try:
            with open(TEMP_FILE_PATH, 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
                results = temp_data.get("results")
                dashboard_data_json = temp_data.get("dashboard_data_json")
        except (json.JSONDecodeError, FileNotFoundError):
            print("一時ファイルの読み込みに失敗しました。")
            
    return render_template('tool.html', results=results, dashboard_data_json=dashboard_data_json)

@app.route('/clear')
@login_required
def clear_results():
    if os.path.exists(TEMP_FILE_PATH):
        os.remove(TEMP_FILE_PATH)
    flash('分析結果をクリアしました。', 'info')
    return redirect(url_for('tool'))

@app.route('/download')
@login_required
def download_csv():
    if not os.path.exists(TEMP_FILE_PATH):
        flash('ダウンロードするデータがありません。まず分析を実行してください。', 'info')
        return redirect(url_for('tool'))
    
    with open(TEMP_FILE_PATH, 'r', encoding='utf-8') as f:
        temp_data = json.load(f)
        results = temp_data.get("results")

    if not results:
        flash('ダウンロードするデータがありません。', 'info')
        return redirect(url_for('tool'))

    output = io.StringIO()
    fieldnames = ['商品名', 'ブランド名', '在庫ステータス', '大カテゴリ', '中カテゴリ', '小カテゴリ', '価格','アクセス数', 'お気に入り登録数', 'お問い合わせ数', '注文情報', '成約日','出品日', '買付地', '発送地', '商品ページURL']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=buyma_analysis.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return response

if __name__ == '__main__':
    app.run(debug=True)