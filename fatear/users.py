import functools
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from fatear.db import get_db

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
def index():
    return render_template('users/index.html')

@bp.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        return find_user(request)
    
    return render_template('users/search.html')

@bp.route('/results')
def find_user(search):
    username = search.form['username']
    db = get_db()
    cursor = db.cursor()

    if username == '':
        flash('Please enter a username')
        return redirect(url_for('users.search'))

    query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(query, (username))
    results = cursor.fetchall()
    cursor.close()

    if not results:
        flash('No user found!')
        return redirect(url_for('users.search'))
    else:
        return render_template('users/results.html', results=results)
    
@bp.route('/profile/<username>', methods=('GET', 'POST'))
def profile(username):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        requester = g.user['username']
        now = datetime.today()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        if "follow" in request.form:
            insert = "INSERT INTO follows VALUES(%s, %s, %s)"
            cursor.execute(insert, (requester, username, formatted_date))
        
        elif "request" in request.form:
            status = 'Pending'
            insert = "INSERT INTO friend VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert, (requester, username, status, requester, formatted_date, formatted_date))
            
        db.commit()
        cursor.close()
        return redirect(url_for('users.profile', username=username))
    
    self = g.user['username']
    is_following = False
    is_friend = False
    is_self = False
    pending_request = False
    requestedBy = ""

    follow_query = "SELECT * FROM follows WHERE follower = %s AND follows = %s"
    cursor.execute(follow_query, (self, username))
    follow_result = cursor.fetchone()

    friend_pending_query = "SELECT * FROM friend WHERE ((user1 = %s AND user2 = %s) OR ((user1 = %s AND user2 = %s))) AND acceptStatus = %s"
    cursor.execute(friend_pending_query, (self, username, username, self, 'Pending'))
    friend_pending_result = cursor.fetchone()

    friend_accepted_query = "SELECT * FROM friend WHERE ((user1 = %s AND user2 = %s) OR ((user1 = %s AND user2 = %s))) AND acceptStatus = %s"
    cursor.execute(friend_accepted_query, (self, username, username, self, 'Accepted'))
    friend_accepted_result = cursor.fetchone()

    if g.user['username'] == username:
        is_self = True

    if follow_result:
        is_following = True

    if friend_pending_result:
        pending_request = True
        requestedBy = friend_pending_result['requestSentBy']

    if friend_accepted_result:
        is_friend = True

    cursor.close()
    return render_template('users/profile.html', self=self, username=username, is_self=is_self,  is_following=is_following, pending_request=pending_request, is_friend=is_friend, requested_by_user=bool(requestedBy == self))

@bp.route('/profile/<username>/following')
def following(username):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM follows WHERE follower = %s"
    cursor.execute(query, (username))
    results = cursor.fetchall()
    cursor.close()
    return render_template('users/following.html', username=username, results=results)

@bp.route('/profile/<username>/followers')
def followers(username):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM follows WHERE follows = %s"
    cursor.execute(query, (username))
    results = cursor.fetchall()
    cursor.close()
    return render_template('users/followers.html', username=username, results=results)

@bp.route('/profile/<username>/send_request')
def send_request(username):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM follows WHERE follows = %s"
    cursor.execute(query, (username))
    results = cursor.fetchall()
    cursor.close()
    return render_template('users/followers.html', username=username, results=results)

@bp.route('/requests')
def view_requests():
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM friend WHERE user2 = %s AND acceptStatus = 'Pending'"
    cursor.execute(query, (g.user['username']))
    results = cursor.fetchall()
    cursor.close()
    return render_template('users/requests.html', results=results)