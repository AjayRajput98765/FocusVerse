from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, date as date_class, timedelta
import random
import json
import google.generativeai as genai
from collections import defaultdict

app = Flask(__name__)

genai.configure(api_key="YOUR_GEMINI_API_KEY")

def generate_learning_plan(topic, duration):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"Create a {duration}-day learning plan to master {topic} with daily goals."
    response = model.generate_content(prompt)
    return response.text

def get_db_connection():
    conn = sqlite3.connect('progress.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                topic TEXT,
                time_spent TEXT,
                feeling TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                journal_text TEXT,
                win1 TEXT,
                win2 TEXT,
                win3 TEXT
            )
        ''')
        conn.commit()

init_db()

def get_random_quote():
    with open('quotes.json', 'r', encoding='utf-8') as f:
        quotes = json.load(f)
    return random.choice(quotes)

def get_weekly_progress_data():
    with get_db_connection() as conn:
        recent_logs = conn.execute("SELECT date FROM progress ORDER BY date DESC LIMIT 30").fetchall()

    counts = defaultdict(int)
    today_date = date_class.today()
    for log in recent_logs:
        log_date = datetime.strptime(log['date'], '%Y-%m-%d').date()
        delta_days = (today_date - log_date).days
        if 0 <= delta_days < 7:
            counts[str(log_date)] += 1

    labels = []
    data = []
    for i in range(6, -1, -1):
        day = today_date - timedelta(days=i)
        labels.append(day.strftime('%a %d'))
        data.append(counts.get(str(day), 0))

    return labels, data


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'journal_text' in request.form:
            journal_text = request.form.get('journal_text')
            win1 = request.form.get('win1')
            win2 = request.form.get('win2')
            win3 = request.form.get('win3')
            today_str = datetime.now().strftime('%Y-%m-%d')

            with get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO journal (date, journal_text, win1, win2, win3)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        journal_text=excluded.journal_text,
                        win1=excluded.win1,
                        win2=excluded.win2,
                        win3=excluded.win3
                ''', (today_str, journal_text, win1, win2, win3))
                conn.commit()

        else:
            topic = request.form.get('topic')
            time_spent = request.form.get('time_spent')
            feeling = request.form.get('feeling')
            date_str = datetime.now().strftime('%Y-%m-%d')

            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO progress (date, topic, time_spent, feeling) VALUES (?, ?, ?, ?)",
                    (date_str, topic, time_spent, feeling)
                )
                conn.commit()

        return redirect('/')

    with get_db_connection() as conn:
        logs = conn.execute("SELECT * FROM progress ORDER BY id DESC").fetchall()
        today_str = datetime.now().strftime('%Y-%m-%d')
        journal = conn.execute("SELECT * FROM journal WHERE date = ?", (today_str,)).fetchone()

    labels, data = get_weekly_progress_data()
    quote = get_random_quote()

    return render_template(
        "index.html",
        quote=quote,
        logs=logs,
        journal=journal,
        chart_labels=labels,
        chart_data=data
    )


if __name__ == '__main__':
    app.run(debug=True)
