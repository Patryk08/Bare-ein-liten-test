from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
import os

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = 'secret-key'
DATABASE = 'database/pizzeria.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT "user")')
    c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, price REAL NOT NULL)')
    
    if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        c.execute('INSERT INTO users VALUES (1, "user1", ?, "user")', (generate_password_hash('password123'),))
        c.execute('INSERT INTO users VALUES (2, "admin", ?, "admin")', (generate_password_hash('admin123'),))
    
    if c.execute('SELECT COUNT(*) FROM menu').fetchone()[0] == 0:
        for item in [('Margherita', 'Tomatsaus, mozzarella og basilikum', 179),
                     ('Pepperoni', 'Tomatsaus, mozzarella og pepperoni', 199),
                     ('Quattro Formaggi', 'Quattro oster blandning', 229),
                     ('Vegetariana', 'Tomatsaus, mozzarella, paprika, løk og oliven', 199)]:
            c.execute('INSERT INTO menu (name, description, price) VALUES (?, ?, ?)', item)
    
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_db().execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or user['role'] != 'admin':
            return redirect(url_for('menu'))
        return f(*args, **kwargs)
    return wrap

@app.route('/')
def index():
    if 'user_id' in session:
        user = get_db().execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return redirect(url_for('admin' if user['role'] == 'admin' else 'menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_db().execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = username
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
    items = get_db().execute('SELECT * FROM menu').fetchall()
    return render_template('menu.html', items=items)

@app.route('/admin')
@admin_required
def admin():
    items = get_db().execute('SELECT * FROM menu').fetchall()
    return render_template('admin.html', items=items)

@app.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        if name and price:
            try:
                get_db().execute('INSERT INTO menu (name, description, price) VALUES (?, ?, ?)',
                               (name, description, float(price)))
                get_db().commit()
                return redirect(url_for('admin'))
            except: pass
    return render_template('add_item.html')

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_item(item_id):
    item = get_db().execute('SELECT * FROM menu WHERE id = ?', (item_id,)).fetchone()
    if not item:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        if name and price:
            try:
                get_db().execute('UPDATE menu SET name = ?, description = ?, price = ? WHERE id = ?',
                               (name, description, float(price), item_id))
                get_db().commit()
                return redirect(url_for('admin'))
            except: pass
    return render_template('edit_item.html', item=item)

@app.route('/admin/delete/<int:item_id>')
@admin_required
def delete_item(item_id):
    get_db().execute('DELETE FROM menu WHERE id = ?', (item_id,))
    get_db().commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
