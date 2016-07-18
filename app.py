# -*- coding: utf-8 -*-
"""Love Wall"""
import datetime
import flask
import flask_sqlalchemy
import werkzeug.exceptions


# Models

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = flask_sqlalchemy.SQLAlchemy(app)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String())
    location_name = db.Column(db.String())
    latitude = db.Column(db.Float())
    longitude = db.Column(db.Float())
    date = db.Column(db.Date())
    description = db.Column(db.Text())


# Views

bp = flask.Blueprint('app', __name__)


@bp.route('/')
def home():
    return flask.render_template('pages/home.html')


@bp.route('/events')
def events():
    return flask.jsonify({
        'events': [{
            'id': e.id,
            'coords': [e.longitude, e.latitude],
            'name': e.location_name,
        } for e in Event.query.all()],
    })


@bp.route('/events/<int:id>')
def event_page(id):
    event = Event.query.filter(Event.id==id).first_or_404()
    return flask.render_template('pages/event.html', event=event)


@bp.route('/admin', methods=['GET', 'POST'])
def admin():
    def populate_from_form(event, form, suffix):
        event.event_name = form['event_name%s' % suffix]
        event.location_name = form['location_name%s' % suffix]
        event.latitude = float(form['latitude%s' % suffix])
        event.longitude = float(form['longitude%s' % suffix])
        event.date = datetime.datetime.strptime(
            form['date%s' % suffix], '%Y-%m-%d').date()
        event.description = form['description%s' % suffix]

    if flask.request.method == 'POST':
        try:
            for event in Event.query.all():
                try:
                    populate_from_form(event, flask.request.form, suffix)
                    db.session.add(event)
                except KeyError:
                    # The event was removed
                    db.session.remove(event)
            for new_suffix in flask.request.form.get('new', '').split(','):
                event = Event()
                populate_from_form(event, flask.request.form, new_suffix)
                db.session.add(event)
        except ValueError:
            flask.flash('You gave me bad data!')
            db.session.rollback()
        else:
            db.session.commit()
    return flask.render_template('pages/admin.html', events=Event.query.all())


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
    db.init_app(app)
    app.register_blueprint(bp)

    def handle_error(exc):
        if not isinstance(exc, werkzeug.exceptions.HTTPException):
            exc = werkzeug.exceptions.InternalServerError()
        message = ("It looks like you're lost" if exc.code == 404
                   else exc.message)
        return flask.render_template(
            'pages/error.html',
             code=exc.code,
             message=message
        ), exc.code

    for status in werkzeug.exceptions.default_exceptions:
        app.errorhandler(status)(handle_error)

    @app.after_request
    def add_csp_header(response):
        csp = app.config.get('CONTENT_SECURITY_POLICY')
        if csp:
            response.headers['Content-Security-Policy'] = csp
        return response

    @app.before_first_request
    def createdb():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.config['SECRET_KEY'] = 'bm90IHRoZSBwcm9kIGtleQ'
    app.config['DEBUG'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.run()
