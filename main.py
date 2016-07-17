import app

application = app.create_app()
application.config['CONTENT_SECURITY_POLICY'] = (
    "script-src: 'unsafe-inline' https://d3js.org"
