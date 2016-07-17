# -*- coding: utf-8 -*-
"""Love Wall"""
import flask
import werkzeug.exceptions


bp = flask.Blueprint('app', __name__)


@bp.route('/')
def home():
    return flask.render_template('home.html')


class App(flask.Flask):

    def send_static_file(self, filename):
        """Send static file, optionally using a compressed version."""
        accept_encoding = flask.request.headers.get('Accept-Encoding', '')
        cache_timeout = self.get_send_file_max_age(filename)
        if 'gzip' in accept_encoding.lower():
            try:
                response = flask.send_from_directory(
                    self.static_folder,
                    filename + '.gz',
                    cache_timeout=cache_timeout,
                )
                response.headers['Content-Encoding'] = 'gzip'
                return response
            except werkzeug.exceptions.NotFound:
                pass
        return flask.send_from_directory(self.static_folder, filename,
                                         cache_timeout=cache_timeout)


def create_app():
    app = App(__name__)
    app.register_blueprint(bp)

    @app.after_request
    def add_csp_header(response):
        csp = app.config.get('CONTENT_SECURITY_POLICY'):
        if csp:
            response.headers['Content-Security-Policy'] = csp
        return response

    return app


if __name__ == '__main__':
    app = create_app()
    app.config['DEBUG'] = True
    app.run()
