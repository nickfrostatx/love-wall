import app
import os

application = app.create_app()
application.config['CONTENT_SECURITY_POLICY'] = (
    "script-src: 'self' https://d3js.org"
)
application.config['SECRET_KEY'] = os.environ['SECRET_KEY']
application.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
