import flask_bootstrap
import hiddifypanel
from dynaconf import FlaskDynaconf
from flask import Flask, request, g
from flask_babelex import Babel
from hiddifypanel.panel.init_db import init_db

from hiddifypanel.models import *
from dotenv import dotenv_values
import os
from hiddifypanel.panel import hiddify
from apiflask import APIFlask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(cli=False, **config):
    
    app = APIFlask(__name__, static_url_path="/<proxy_path>/static/", instance_relative_config=True, version='2.0.0', title="Hiddify API",
                   openapi_blueprint_url_prefix="/<proxy_path>/<user_secret>/api", docs_ui='elements', json_errors=False, enable_openapi=True)
    # app = Flask(__name__, static_url_path="/<proxy_path>/static/", instance_relative_config=True)
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
    app.servers = {
        'name': 'current',
        'url': '',
    }
    app.info = {
        'description': 'Hiddify is a free and open source software. It is as it is.',
        'termsOfService': 'http://hiddify.com',
        'contact': {
            'name': 'API Support',
            'url': 'http://www.hiddify.com/support',
            'email': 'panel@hiddify.com'
        },
        'license': {
            'name': 'Creative Commons Zero v1.0 Universal',
            'url': 'https://github.com/hiddify/Hiddify-Manager/blob/main/LICENSE'
        }
    }

    for c, v in dotenv_values(os.environ.get("HIDDIFY_CFG_PATH", 'app.cfg')).items():
        if v.isdecimal():
            v = int(v)
        else:
            v = True if v.lower() == "true" else (False if v.lower() == "false" else v)

        app.config[c] = v

    app.jinja_env.line_statement_prefix = '%'
    app.jinja_env.filters['b64encode'] = hiddify.do_base_64
    app.view_functions['admin.static']={}#fix bug in apiflask
    app.is_cli = cli
    flask_bootstrap.Bootstrap4(app)

    hiddifypanel.panel.database.init_app(app)
    with app.app_context():
        # hiddifypanel.panel.database.init_migration(app)
        # hiddifypanel.panel.database.migrate()
        # hiddifypanel.panel.database.upgrade()
        init_db()

    hiddifypanel.panel.common.init_app(app)
    hiddifypanel.panel.admin.init_app(app)
    hiddifypanel.panel.user.init_app(app)
    hiddifypanel.panel.commercial.init_app(app)
    hiddifypanel.panel.cli.init_app(app)

    app.config.update(config)  # Override with passed config
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False

    # app.config['BABEL_TRANSLATION_DIRECTORIES'] = '/workspace/Hiddify-Server/hiddify-panel/src/translations.i18n'
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        # Put your logic here. Application can store locale in
        # user profile, cookie, session, etc.
        from hiddifypanel.models import ConfigEnum, hconfig
        if "admin" in request.base_url:
            g.locale = hconfig(ConfigEnum.admin_lang) or hconfig(ConfigEnum.lang) or 'fa'
        else:
            g.locale = hconfig(ConfigEnum.lang) or "fa"
        return g.locale

    from flask_wtf.csrf import CSRFProtect

    csrf = CSRFProtect(app)

    @app.before_request
    def check_csrf():
        if "/admin/user/" in request.base_url:
            return
        if "/admin/domain/" in request.base_url:
            return
        if "/admin/actions/" in request.base_url:
            return
        if "/api/" in request.base_url:
            return
        csrf.protect()

    @app.after_request
    def apply_no_robot(response):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
    app.jinja_env.globals['get_locale'] = get_locale
    app.jinja_env.globals['version'] = hiddifypanel.__version__
    app.jinja_env.globals['static_url_for'] = hiddify.static_url_for

    return app


def create_app_wsgi():
    # workaround for Flask issue
    # that doesn't allow **config
    # to be passed to create_app
    # https://github.com/pallets/flask/issues/4170
    app = create_app()
    return app


# def create_cli_app():
#     # workaround for Flask issue
#     # that doesn't allow **config
#     # to be passed to create_app
#     # https://github.com/pallets/flask/issues/4170
#     app = create_app(cli=True)
#     return app
