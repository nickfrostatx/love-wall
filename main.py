import app

application = app.create_app()
application.config['CONTENT_SECURITY_POLICY'] = (
    "script-src: 'self' https://d3js.org"
)
