
from flask import Flask, render_template, request, redirect, session, g, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
DATABASE = 'chat_fancy.db'

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

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL)''')
        db.commit()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            error = "Please fill all fields"
        else:
            db = get_db()
            try:
                db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                db.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = "Username already taken"
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password"
    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    if request.method == 'POST':
        message = request.form['message'].strip()
        if message:
            db.execute("INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)",
                       (session['username'], message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()

    chats = db.execute("SELECT id, sender, message, timestamp FROM messages ORDER BY id DESC LIMIT 50").fetchall()
    return render_template('dashboard.html', user=session['username'], chats=chats[::-1])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    db = get_db()
    msg = db.execute("SELECT * FROM messages WHERE id=?", (msg_id,)).fetchone()
    if msg is None:
        return jsonify({"error": "Message not found"}), 404
    if msg['sender'] != session['username']:
        return jsonify({"error": "Not authorized"}), 403

    db.execute("DELETE FROM messages WHERE id=?", (msg_id,))
    db.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
