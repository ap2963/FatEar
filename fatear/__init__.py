import os
from flask import Flask, g, redirect, render_template, request, session, url_for
from flask import Flask, render_template, redirect, url_for

def create_app(test_config=None):
    from . import db, auth, users, music

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev'
    )

    if test_config is None:
    # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    
    else:
    # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
                        
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(music.bp)

    # home page
    @app.route('/')
    def home():
        if g.user is None:
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('users.index'))
        
    return app

