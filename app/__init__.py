import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from config import Config
from flask_bootstrap import Bootstrap
from flask_talisman import Talisman
app = Flask(__name__)
app.config.from_object(Config)
talisman = Talisman(app, content_security_policy=Config.csp)
bootstrap = Bootstrap(app)
from app import routes, errors

app.config['TEMPLATES_AUTO_RELOAD'] = True


def create_app(config_class=Config):
    if not app.debug and not app.testing:
        # ...

        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/glycomass.log',
                                               maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Glycomass startup')

    return app

