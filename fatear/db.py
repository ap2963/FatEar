from flask import current_app, g
import pymysql
import pymysql.cursors
import click

def get_db():
    if 'db' not in g:
        #MySQL(current_app) returns a connection object, which is stored in g
        g.db = pymysql.connect(host='localhost',
                               user='root',
                               password='root',
                               port=8889,
                               database='fatear',
                               cursorclass=pymysql.cursors.DictCursor)
    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql', 'r') as f:
        with db.cursor() as cursor:
            cursor.execute(f.read())
        db.commit()

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)