from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps
import os

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = 'secret-key'
DATABASE = 'database/pizzeria.db'


def get_db():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('DROP TABLE IF EXISTS users')
        conn.execute('DROP TABLE IF EXISTS menu')
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)')
        conn.execute('CREATE TABLE menu (id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL)')

        conn.executemany(
            'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
            [
                ('user1', 'password123', 'user'),
                ('admin', 'admin123', 'admin')
            ]
        )

        menu_items = [
            ('Margherita', 'Tomatsaus, mozzarella og basilikum', 179),
            ('Pepperoni', 'Tomatsaus, mozzarella og pepperoni', 199),
            ('Quattro Formaggi', 'Quattro oster blandning', 229),
            ('Vegetariana', 'Tomatsaus, mozzarella, paprika, løk og oliven', 199)
        ]
        conn.executemany('INSERT INTO menu (name, description, price) VALUES (?, ?, ?)', menu_items)


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap


@app.route('/')
def index():
    if session.get('role') == 'admin':
        return redirect(url_for('admin'))
    if 'username' in session:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and user['password'] == password:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('admin' if user['role'] == 'admin' else 'menu'))
        error = 'Feil brukernavn eller passord'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/menu')
@login_required
def menu():
    with get_db() as conn:
        items = conn.execute('SELECT * FROM menu').fetchall()
    return render_template('menu.html', items=items)


@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('menu'))
    with get_db() as conn:
        items = conn.execute('SELECT * FROM menu').fetchall()
    return render_template('admin.html', items=items)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
