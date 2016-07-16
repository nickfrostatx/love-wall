# -*- coding: utf-8 -*-
"""Love Wall"""
import flask


bp = flask.Blueprint('app', __name__)


@bp.route('/')
def home():
    return flask.render_template('home.html')


def create_app():
    app = flask.Flask(__name__)
    app.register_blueprint(bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.config['DEBUG'] = True
    app.run()
