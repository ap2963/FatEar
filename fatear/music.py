from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
# from fatear.forms import MusicSearchForm
from fatear.db import get_db

bp = Blueprint('music', __name__, url_prefix='/music')

class SongsDict:
    def create_songs_dict():
        db = get_db()
        cursor = db.cursor()
        songs_dict = {}

        query1 = "SELECT * FROM song"
        songs = cursor.execute(query1).fetchall()
        for song in songs:
            song_id = song["songID"]

            query2 = "SELECT DISTINCT artist.fname, artist.lname FROM artistPerformsSong NATURAL JOIN artist WHERE songID = %s"
            songs_dict['artists'] = cursor.execute(query2(song_id)).fetchall()

            query3 = "SELECT genre FROM songGenre WHERE songID = %s"
            songs_dict['genres'] = cursor.execute(query3(song_id)).fetchall()
    
            cursor.close()
        
        return songs_dict
    
    def __init__(self, *args, **kwargs):
        self.dict = self.create_songs_dict()
    

@bp.route('/', methods=('GET', 'POST'))
def main():
    if request.method == 'POST':
        return search_results(request)
    
    return render_template('music/main.html')
    
#fetchall() returns an empty list or a list of tuples
#fetchone() returns a single record or None
@bp.route('/results')
def search_results(search):
    song_title = search.form['song_title'] #data is a dict containing the data for each field

    db = get_db()
    cursor = db.cursor()

    if song_title == '':
        query = "SELECT * FROM song NATURAL LEFT JOIN artistPerformsSong NATURAL LEFT JOIN songInAlbum NATURAL LEFT JOIN songGenre"
        cursor.execute(query)
    else:
        query = "SELECT * FROM song NATURAL LEFT JOIN artistPerformsSong NATURAL LEFT JOIN songInAlbum NATURAL LEFT JOIN songGenre WHERE song.title = %s"
        cursor.execute(query, (song_title))
        
    results = cursor.fetchall()
    cursor.close()

    #show all songs
    if not results:
        flash('No results found!')
        return redirect('/')
    else:
        return render_template('music/results.html', results=results)

# #account for many-to-many relationships (artist and genre)
# def format_song(song_ID):
#     db = get_db()
#     cursor = db.cursor()
#     query = "SELECT * FROM song WHERE songID = %s"
#     cursor.execute(query, song_ID)
#     results = cursor.fetchall()
    
#     cursor.close()

@bp.route('/create_song', methods=('GET', 'POST'))
def create_song():
    if request.method == 'POST':
        title = request.form['title']
        release_date = request.form['release_date']
        url = request.form['url']
        db = get_db()
        error = None

        cursor = db.cursor()
        insert = "INSERT INTO song VALUES(%s, %s, %s)"
        cursor.execute(insert, (title, release_date, url))
        db.commit()
        cursor.close()
        return render_template('music/main.html')
