from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from fatear.db import get_db
from fatear.auth import login_required
from fatear.music import artist_page, song_details

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/', methods=('GET', 'POST'))
def dashboard():
    curr_user = g.user['username']
    db = get_db()
    cursor = db.cursor()
    error = None

    #user info
    query = "SELECT username, fname, lname, nickname, lastlogin FROM user WHERE username = %s"
    cursor.execute(query, (curr_user))
    user_info = cursor.fetchall()

    #user friends
    query = "(SELECT t1.user1 FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t1 WHERE t1.user1 != %s) UNION (SELECT t2.user2 FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t2 WHERE t2.user2 != %s)"
    cursor.execute(query, (curr_user, curr_user, curr_user, curr_user, curr_user, curr_user))
    friends = cursor.fetchall()

    #user is following
    query = "SELECT f.follows FROM follows AS f WHERE f.follower = %s AND f.follows != %s"
    cursor.execute(query, (curr_user, curr_user))
    followers = cursor.fetchall()

    #user artists
    query = "SELECT artistID FROM userFanOfArtist WHERE username = %s"
    cursor.execute(query, (curr_user))
    artists = cursor.fetchall()

    cursor.close()
    if error:
        flash(error)

    return render_template('users/dashboard.html', details=user_info, friends=friends, followers=followers, artists=artists)

@bp.route('/new-activity', methods=('GET', 'POST'))
def view_new_activity():
    curr_user = g.user['username']
    db = get_db()
    cursor = db.cursor()
    error = None

    #used to get follower/friend info
    query = "SELECT fname, lname, username FROM user"
    cursor.execute(query)
    user_info = cursor.fetchall()

    #user friends
    friend_query = "(SELECT t1.user1 FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t1 WHERE t1.user1 != %s) UNION (SELECT t2.user2 FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t2 WHERE t2.user2 != %s)"
    cursor.execute(friend_query, (curr_user, curr_user, curr_user, curr_user, curr_user, curr_user))
    friends = cursor.fetchall()

    #user is following
    follow_query = "SELECT f.follows FROM follows AS f WHERE f.follower = %s AND f.follows != %s"
    cursor.execute(follow_query, (curr_user, curr_user))
    followers = cursor.fetchall()

    #new ratings
    query = "SELECT * FROM rateSong WHERE ratingDate > (SELECT lastlogin FROM user WHERE username = %s) AND (username IN (%s) OR username IN (%s))"
    cursor.execute(query, (curr_user, friend_query, follow_query))
    new_ratings = cursor.fetchall()

    #new reviews
    query = "SELECT * FROM reviewSong WHERE reviewDate > (SELECT lastlogin FROM user WHERE username = %s)"
    cursor.execute(query, (curr_user))
    new_reviews = cursor.fetchall()

    #songs and who performs them
    query = "SELECT s.songID, s.title, a.fname, a.lname FROM song AS s NATURAL JOIN artistPerformsSong AS p NATURAL JOIN artist AS a"
    cursor.execute(query)
    songs = cursor.fetchall()
    
    cursor.close()

    if error:
        flash(error)

    return render_template('users/new.html', user=curr_user, friends=friends, followers=followers, ratings=new_ratings, reviews=new_reviews, songs=songs, user_info=user_info)

@bp.route('/new-artist-activity', methods=('GET', 'POST'))
def view_new_artist_activity():
    curr_user = g.user['username']
    db = get_db()
    cursor = db.cursor()
    error = None

    #new songs from user's followed artists
    query = "SELECT * FROM artist NATURAL JOIN (SELECT * FROM song NATURAL JOIN (SELECT artistID FROM userFanOfArtist WHERE username = %s) as t1) as t2 WHERE releaseDate > (SELECT lastlogin FROM user WHERE username = %s)"
    cursor.execute(query, (curr_user, curr_user))
    releases = cursor.fetchall()

    #used to list artists for the song
    query = "SELECT * FROM song NATURAL JOIN artistPerformsSong NATURAL JOIN artist"
    cursor.execute(query)
    songs = cursor.fetchall()

    cursor.close()

    if error:
        flash(error)

    return render_template('users/new_music.html', user=curr_user, releases=releases, songs=songs)

@bp.route('/search', methods=('GET', 'POST'))
def search_users():
    if request.method == 'POST':
        search = request.form['search']
        term = "%" + search + "%" 

        db = get_db()
        cursor = db.cursor()
        query = "SELECT * FROM (SELECT username, nickname, CONCAT(fname, ' ', lname) AS name FROM user) AS s WHERE s.name LIKE %s OR s.username LIKE %s"
        cursor.execute(query, (term, term))
        results = cursor.fetchall()
   
        cursor.close()

        if not results:
            flash('No user found')
            return redirect(url_for('users.search_users'))
        return render_template('users/results.html', users=results)
        
    return render_template('users/search.html')

@bp.route('/search-results', methods=('GET',))
def results():
    return render_template('users/results.html')

@bp.route('/profile/<username>', methods=('GET', 'POST'))
def view_profile(username):     
    curr_user = g.user['username']
    profile = username
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        query = "SELECT * FROM follows AS f WHERE f.follower = %s AND f.follows = %s"
        cursor.execute(query, (curr_user, profile))
        follow_record = cursor.fetchone()

        if not follow_record:
            now = datetime.today()
            formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
            insert = "INSERT INTO follows VALUES (%s, %s, %s)"
            cursor.execute(insert, (curr_user, profile, formatted_date))
            db.commit()
            flash("Success!")
            return render_template('users/dashboard.html')
        else:
            flash('You are already following this user')
            return redirect(url_for('users.view_profile', username=profile))

    view = "restricted"
    friend_record = None
    if curr_user == profile:
        view = "self"
    else:
        db = get_db()
        cursor = db.cursor()

        query = "SELECT * FROM follows AS f WHERE f.follower = %s AND f.follows = %s"
        cursor.execute(query, (curr_user, profile))
        follow_record = cursor.fetchone()

        users = (curr_user, profile)
        query = "SELECT * FROM friend WHERE user1 = %s AND user2 = %s"
        cursor.execute(query, (min(users), max(users)))
        friend_record = cursor.fetchone()
      
        if follow_record:
            if friend_record:
                if friend_record['acceptStatus'] == 'Accepted':
                    view = "friend"
                elif friend_record['acceptStatus'] == 'Pending':
                    if friend_record['requestSentBy'] == curr_user:
                        view = 'pending'
                    else:
                        view = 'request-sent'
                else:
                    view = 'follower'
            else:
                view = "follower"

    query = "SELECT fname, lname, nickname FROM user WHERE username = %s" 
    cursor.execute(query, (profile))
    details = cursor.fetchone()
    cursor.close()

    return render_template('users/profile.html', user=curr_user, view=view, profile=profile, details=details)

@bp.route('/profile/<username>/connections', methods=('GET', 'POST'))
def see_user_connections(username):
    curr_user = g.user['username'] 
    profile = username
    db = get_db()
    cursor = db.cursor()

    #user details
    query = "SELECT fname, lname, nickname FROM user WHERE username = %s" 
    cursor.execute(query, (profile))
    details = cursor.fetchone()

    query = "SELECT * FROM follows JOIN user ON (follows.follows = user.username) WHERE follower = %s"
    cursor.execute(query, (username))
    following = cursor.fetchall()

    query = "SELECT * FROM follows JOIN user ON (follows.follower = user.username) WHERE follows = %s"
    cursor.execute(query, (username))
    followers = cursor.fetchall()

    query = "(SELECT t1.user1 AS username FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t1 WHERE t1.user1 != %s) UNION (SELECT t2.user2 AS username FROM (SELECT * FROM friend WHERE user1 = %s OR user2 = %s AND acceptStatus = 'Accepted') AS t2 WHERE t2.user2 != %s)"
    cursor.execute(query, (profile, profile, profile, profile, profile, profile))
    friends = cursor.fetchall()

    #details to get fname, lname
    query = "SELECT username, fname, lname FROM user" 
    cursor.execute(query)
    users = cursor.fetchall()

    cursor.close()
    return render_template('users/connects.html', following=following, followers=followers, friends=friends, users=users, self=curr_user, profile=profile, details=details)


@bp.route('/profile/<username>/activty', methods=('GET', 'POST'))
def see_user_activity(username):
    curr_user = g.user['username'] 
    profile = username
    db = get_db()
    cursor = db.cursor()

    #user details
    query = "SELECT fname, lname, nickname FROM user WHERE username = %s" 
    cursor.execute(query, (profile))
    details = cursor.fetchone()

    #user's ratings
    query = "SELECT * FROM rateSong WHERE username = %s"
    cursor.execute(query, (curr_user))
    ratings = cursor.fetchall()

    #user's reviews
    query = "SELECT * FROM reviewSong WHERE username = %s"
    cursor.execute(query, (curr_user))
    reviews = cursor.fetchall()

    #songs and who performs them
    query = "SELECT s.songID, s.title, a.fname, a.lname FROM song AS s NATURAL JOIN artistPerformsSong AS p NATURAL JOIN artist AS a"
    cursor.execute(query)
    songs = cursor.fetchall()
    
    return render_template('users/user_activity.html', profile=profile, details=details, ratings=ratings, reviews=reviews, songs=songs)

@bp.route('/profile/<username>/send_request', methods=('GET', 'POST'))
def send_request(username):
    curr_user = g.user['username']
    profile = username
    db = get_db()
    cursor = db.cursor()
    error=None

    query = "SELECT * FROM friend WHERE user1 = %s and user2 = %s"
    cursor.execute(query, (min(curr_user, profile), max(curr_user, profile)))
    record = cursor.fetchone()

    if record:
        if record['acceptStatus'] == 'Pending':
            flash("Pending request already exists")
            return redirect(url_for('users.view_profile', username=profile))
        elif record['acceptStatus'] == 'Accepted':
            flash("Already friends")
            return redirect(url_for('users.view_profile', username=profile))

    now = datetime.today()
    formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
    insert = "INSERT INTO friend VALUES(%s, %s, %s, %s, %s, %s)"
    cursor.execute(insert, (min(curr_user, username), max(curr_user, username), 'Pending', curr_user, formatted_date, formatted_date))
    db.commit()
    flash('Friend request sent')
    cursor.close()

    if error:
        flash(error)

    return render_template('users/dashboard.html')

@bp.route('/requests', methods=('GET', 'POST'))
def check_requests():
    curr_user = g.user['username']
    db = get_db()
    cursor = db.cursor()
    error = None

    query = "SELECT * FROM friend WHERE (user1 = %s OR user2 = %s) AND acceptStatus = 'Pending' AND requestSentBy != %s"
    cursor.execute(query, (curr_user, curr_user, curr_user))
    requests = cursor.fetchall()

    query = "SELECT username, fname, lname, nickname FROM user"
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()
    return render_template('users/requests.html', requests=requests, users=users)


@bp.route('/respond/<username>', methods=('GET', 'POST',))
def respond(username):
    if request.method == 'POST':
        curr_user = g.user['username']
        db = get_db()
        cursor = db.cursor()
        error = None
        if "accept" in request.form:
            now = datetime.today()
            formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
            update = "UPDATE friend SET acceptStatus = %s, updatedAt = %s WHERE user1 = %s AND user2 = %s"
            cursor.execute(update, ('Accepted', formatted_date, min(curr_user, username), max(curr_user, username)))
            flash("Success!")
            db.commit()
        else:
            now = datetime.today()
            formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
            update = "UPDATE friend SET acceptStatus = %s, updatedAt = %s WHERE user1 = %s AND user2 = %s"
            cursor.execute(update, ('Not accepted', formatted_date, min(curr_user, username), max(curr_user, username)))
            flash("Success!")
            db.commit()
            
        if error:
            flash(error)
        return redirect(url_for('users.check_requests'))
    
    return render_template('users/respond.html', profile=username)


@bp.route('/artist/follow', methods=('GET', 'POST'))
def follow_artist():     
    curr_user = g.user['username']
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        artist = request.form['artist']
        insert = "INSERT INTO userFanOfArtist VALUES (%s, %s)"
        cursor.execute(insert, (curr_user, artist))
        db.commit()
        flash("Success!")
        return render_template('users/dashboard.html')

    #get artists that user is not following
    query = "SELECT * FROM (SELECT artistID FROM artist WHERE artistID NOT IN (SELECT artistID FROM userFanOfArtist WHERE username = %s)) AS t1 NATURAL JOIN artist"
    cursor.execute(query, (curr_user))
    artists = cursor.fetchall()
    cursor.close()

    return render_template('users/follow_artist.html', artists=artists)




