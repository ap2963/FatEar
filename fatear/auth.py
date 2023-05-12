import functools
from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from werkzeug.security import check_password_hash, generate_password_hash
from fatear.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['pwd']
        fname = request.form['fname']
        lname = request.form['lname']
        nickname = request.form['nickname']
        error = None

        db = get_db()
        cursor = db.cursor()
        query = 'SELECT * FROM user WHERE username = %s'
        cursor.execute(query, (username))
        data = cursor.fetchone()

        if data:
            error = f"User {username} is already registered"
            cursor.close()
        else:
            now = datetime.today()
            formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
            insert = "INSERT INTO user VALUES(%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert, (username, pwd, fname, lname, formatted_date, nickname))
            db.commit()
            cursor.close()
            return render_template('users/index.html')
        
        if error:  
          flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['pwd']
        db = get_db()
        error = None

        cursor = db.cursor()
        query = 'SELECT * FROM user WHERE username = %s AND pwd = %s' 
        cursor.execute(query, (username, pwd))
        data = cursor.fetchone()
        cursor.close()

        if data:
            session.clear()
            session['user'] = username
            return redirect(url_for('users.dashboard'))
        else:
            error = "Invalid username or password"
            flash(error)

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user = session.get('user')

    if user is None:
        g.user = None
    else:
        db = get_db()
        cursor = db.cursor()
        query = 'SELECT * FROM user WHERE username = %s' 
        cursor.execute(query, (user))
        g.user = cursor.fetchone()
        cursor.close()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
