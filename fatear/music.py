from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
# from fatear.forms import MusicSearchForm
from fatear.db import get_db
from fatear.auth import login_required

bp = Blueprint('music', __name__, url_prefix='/music')

@bp.route('/', methods=('GET', 'POST'))
def main():    
    if request.method == 'POST':
        return search_results(request)
    
    db = get_db()
    cursor = db.cursor()
    query = "SELECT DISTINCT genre FROM songGenre ORDER BY genre ASC"
    cursor.execute(query)
    genres = cursor.fetchall()
    cursor.close()

    return render_template('music/main.html', genres=genres, registered=bool(g.user))
    
    
@bp.route('/results', methods=('GET', 'POST'))
def search_results(request):
    db = get_db()
    cursor = db.cursor()
    
    #intersect_query = query
    query = "SELECT DISTINCT songID, title, releaseDate, mean_rating FROM (SELECT *, CONCAT(fname, ' ', lname) AS artist_name FROM song LEFT JOIN artistPerformsSong USING (songID) LEFT JOIN songGenre USING (songID) LEFT JOIN artist USING (artistID)) t1 LEFT JOIN (SELECT songID, AVG(stars) AS mean_rating FROM rateSong GROUP BY songID) t2 USING (songID)"
    i = 0
    terms = []

    if request.form['song_title']:
        q = " WHERE t1.title LIKE %s"
        #intersect_query += q
        query += q
        song = '%' + request.form['song_title'] + '%'
        terms.append(song)
        i += 1
    
    if request.form['artist']:
        if i == 0:
            q = " WHERE"
            #intersect_query += q
            query += q
        else:
            #intersect_query += " AND"
            query += " OR"
        q = " artist_name LIKE %s"
        query += q
        #intersect_query += q
        artist = '%' + request.form['artist'] + '%'
        terms.append(artist)
        i += 1
    
    if request.form['genre']:
        if i == 0:
            q = " WHERE"
            #intersect_query += q
            query += q
        else:
            #intersect_query += " AND"
            query += " OR"
        q = " t1.genre = %s"
        #intersect_query += q
        query += q
        terms.append(request.form['genre'])
        i += 1

    if request.form['rating']:
        if i == 0:
            q = " WHERE"
            #intersect_query += q
            query += q
        else:
            #query += " AND"
            union_query += " OR"
        q = " t2.mean_rating >= %s"
        #intersect_query += q
        query += q
        terms.append(request.form['rating'])
        i += 1
        
    cursor.execute(query, terms)
    songs = cursor.fetchall()
    #cursor.execute(intersect_query, terms)
    #songs_from_union = cursor.fetchall()
    
    artists_query = "SELECT * FROM artistPerformsSong NATURAL JOIN artist ORDER BY songID"
    cursor.execute(artists_query)
    artists = cursor.fetchall()

    genres_query = "SELECT * FROM songGenre ORDER BY songID"
    cursor.execute(genres_query)
    genres = cursor.fetchall()
    cursor.close()

    if not songs:
        flash('No songs found')
        return redirect(url_for('music.main'))

    return render_template('music/results.html', songs=songs, artists=artists, genres=genres)


@bp.route('/song/<songID>', methods=('GET', 'POST'))
def song_details(songID):
    db = get_db()
    cursor = db.cursor()
    error = None

    #song details
    query = "SELECT * FROM song WHERE songID = %s"
    cursor.execute(query, (songID))
    song = cursor.fetchone()

    #song's artists
    query = "SELECT fname, lname, artistID FROM song NATURAL JOIN artistPerformsSong NATURAL JOIN artist WHERE songID = %s"
    cursor.execute(query, (songID))
    artists = cursor.fetchall()

    #song's genres
    query = "SELECT genre FROM songGenre WHERE songID = %s"
    cursor.execute(query, (songID))
    genres = cursor.fetchall()

    cursor.close()
    if error: 
        flash(error)

    return render_template('music/song.html', song=song, artists=artists, genres=genres, registered=bool(g.user))
 

@bp.route('/artist/<artistID>', methods=('GET', 'POST'))
def artist_page(artistID):
    db = get_db()
    artist = artistID
    cursor = db.cursor()
    error = None

    #songs by artist
    query = "SELECT * FROM artist NATURAL JOIN (SELECT * FROM song NATURAL JOIN artist WHERE artistID = %s) as t1"
    cursor.execute(query, (artist))
    songs = cursor.fetchall()

    #used to list artists for each song
    query = "SELECT * FROM song NATURAL JOIN artistPerformsSong NATURAL JOIN artist"
    cursor.execute(query)
    all_artists = cursor.fetchall()

    cursor.close()

    if error:
        flash(error)

    return render_template('music/artist.html', all_artists=all_artists, songs=songs, profile=artist, registered=bool(g.user))
 
    
@login_required
@bp.route('/new-rating/<songID>', methods=('GET', 'POST',))
def rate_song(songID):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':    
        curr_user = g.user['username']
        stars = request.form['stars']
        now = datetime.today()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        error = None

        insert = "INSERT INTO rateSong VALUES (%s, %s, %s, %s)"
        cursor.execute(insert, (curr_user, songID, stars, formatted_date))
        db.commit()
        flash('Success!')

        if error:
            flash(error)

        return redirect(url_for('music.song_details', songID=songID))
    
    query = 'SELECT * FROM song WHERE songID = %s'
    cursor.execute(query, (songID))
    song = cursor.fetchone()
    cursor.close()

    return render_template('music/rate.html', song=song)


@login_required
@bp.route('/new-review/<songID>', methods=('GET', 'POST',))
def review_song(songID):
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':  
        curr_user = g.user['username']
        text = request.form['text']
        now = datetime.today()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        error = None

        insert = "INSERT INTO reviewSong VALUES (%s, %s, %s, %s)"
        cursor.execute(insert, (curr_user, songID, text, formatted_date))
        db.commit()
        flash('Success!')

        if error:
            flash(error)

        return redirect(url_for('music.song_details', songID=songID))
    
    query = 'SELECT * FROM song WHERE songID = %s'
    cursor.execute(query, (songID))
    song = cursor.fetchone()

    cursor.close()
    return render_template('music/review.html', song=song)

