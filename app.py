# -*- coding: utf-8 -*-
"""Love Wall"""
import base64
import datetime
import functools
import os

import flask
import flask_sqlalchemy
import sqlalchemy.sql
import werkzeug.exceptions
import werkzeug.security


# Models

app = flask.Flask(__name__)
db = flask_sqlalchemy.SQLAlchemy(app)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String)
    location_name = db.Column(db.String)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    date = db.Column(db.Date)
    description = db.Column(db.Text)

    def get_score(self):
        return self.hearts.count()


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)


class Heart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=sqlalchemy.sql.func.now())
    event_id = db.Column(db.Integer, db.ForeignKey(Event.id))
    event = db.relationship(Event, backref=db.backref('hearts',
                                                      lazy='dynamic'))
    session_id = db.Column(db.Integer, db.ForeignKey(Session.id))
    session = db.relationship(Session,
                              backref=db.backref('hearts', lazy='dynamic'))
    __table_args__ = (db.UniqueConstraint('event_id', 'session_id',
                                          name='uq_event_session'),)


class Sentiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=sqlalchemy.sql.func.now())
    event_id = db.Column(db.Integer, db.ForeignKey(Event.id))
    event = db.relationship(Event, backref=db.backref('sentiments',
                                                      lazy='dynamic'))
    text = db.Column(db.Text)

    def get_score(self):
        ups = self.votes.filter(SentimentVote.direction == 'up').count()
        downs = self.votes.filter(SentimentVote.direction == 'down').count()
        return ups - downs

    def vote_for(self, session_id):
        return (self.votes.filter(SentimentVote.session_id == session_id)
                    .first())


class SentimentVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=sqlalchemy.sql.func.now())
    sentiment_id = db.Column(db.Integer, db.ForeignKey(Sentiment.id))
    sentiment = db.relationship(Sentiment, backref=db.backref('votes',
                                                              lazy='dynamic'))
    session_id = db.Column(db.Integer, db.ForeignKey(Session.id))
    session = db.relationship(Session,
                              backref=db.backref('votes', lazy='dynamic'))
    direction = db.Column(db.Enum('up', 'down'))
    __table_args__ = (db.UniqueConstraint('sentiment_id', 'session_id',
                                          name='uq_sentiment_session'),)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=sqlalchemy.sql.func.now())
    sentiment_id = db.Column(db.Integer, db.ForeignKey(Sentiment.id))
    sentiment = db.relationship(Sentiment, backref=db.backref('comments',
                                                              lazy='dynamic'))
    text = db.Column(db.Text)


# Views

bp = flask.Blueprint('app', __name__)


@bp.before_request
def init_session():
    if 'id' not in flask.session:
        sess = Session()
        db.session.add(sess)
        db.session.commit()
        flask.session['id'] = sess.id
    if 'csrf' not in flask.session:
        token = base64.urlsafe_b64encode(os.urandom(30)).decode('utf-8')
        flask.session['csrf'] = token


def csrf(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        token = flask.request.args.get('token') or \
                flask.request.form.get('token')
        actual = flask.session['csrf']
        if not token or not werkzeug.security.safe_str_cmp(token, actual):
            raise werkzeug.exceptions.BadRequest('Missing CSRF token')
        return fn(*args, **kwargs)
    return wrapped


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
    event = Event.query.filter(Event.id == id).first_or_404()
    hearted = (Heart.query.filter(Heart.event == event,
                                  Heart.session_id == flask.session['id'])
                    .count() != 0)
    sentiments = Sentiment.query.filter(Sentiment.event == event)
    return flask.render_template('pages/event.html', event=event,
                                 hearted=hearted, sentiments=sentiments)


@bp.route('/events/<int:id>/heart')
@csrf
def heart(id):
    event = Event.query.filter(Event.id == id).first_or_404()
    try:
        h = Heart(event=event, session_id=flask.session['id'])
        db.session.add(h)
        db.session.commit()
        return flask.Response(status=204)
    except sqlalchemy.exc.IntegrityError:
        raise werkzeug.exceptions.Conflict('You have already voted')


@bp.route('/sentiments/<int:id>/votes')
@csrf
def sentiment_vote(id):
    sentiment = Sentiment.query.filter(Sentiment.id == id).first_or_404()
    session_id = flask.session['id']
    v = sentiment.vote_for(session_id)
    try:
        how = flask.request.args['how']
        if how in ('up', 'down'):
            if v is None:
                # New vote
                v = SentimentVote(sentiment=sentiment, session_id=session_id,
                                  direction=how)
                db.session.add(v)
                db.session.commit()
            elif v.direction != how:
                # Change existing vote
                v.direction = how
                db.session.add(v)
                db.session.commit()
        elif how == 'none':
            if v is not None:
                # Delete vote
                db.session.delete(v)
                db.session.commit()
        else:
            raise werkzeug.exceptions.BadRequest()
        return flask.redirect(flask.url_for('.event_page',
                              id=sentiment.event.id))
    except sqlalchemy.exc.IntegrityError:
        raise werkzeug.exceptions.Conflict('You have already voted')


@bp.route('/events/<int:id>/sentiments/', methods=['POST'])
@csrf
def post_sentiment(id):
    event = Event.query.filter(Event.id == id).first_or_404()
    sentiment = Sentiment(event=event, text=flask.request.form['text'])
    db.session.add(sentiment)
    db.session.commit()
    return flask.redirect(flask.url_for('.event_page', id=id), code=303)


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
                    populate_from_form(event, flask.request.form, event.id)
                    db.session.add(event)
                except KeyError:
                    # The event was removed
                    db.session.remove(event)
            if flask.request.form.get('new', ''):
                for new_suffix in flask.request.form['new'].split(','):
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
        if exc.code == 404:
            message = "It looks like you're lost"
        else:
            try:
                message = exc.description
            except AttributeError:
                message = "Internal Server Error"
        return flask.render_template('pages/error.html', code=exc.code,
                                     message=message), exc.code

    for status in werkzeug.exceptions.default_exceptions:
        app.errorhandler(status)(handle_error)

    @app.after_request
    def add_csp_header(response):
        csp = app.config.get('CONTENT_SECURITY_POLICY')
        if csp:
            response.headers['Content-Security-Policy'] = csp
        return response

    @app.before_first_request
    def create_db():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.config['SECRET_KEY'] = 'bm90IHRoZSBwcm9kIGtleQ'
    app.config['DEBUG'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.run()
