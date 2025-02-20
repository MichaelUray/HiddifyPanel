import traceback
import uuid

import user_agents
from flask import  render_template, request, jsonify
from flask import g, send_from_directory, session, Markup
from jinja2 import Environment, FileSystemLoader
from flask_babelex import gettext as _
import hiddifypanel
from hiddifypanel.models import *
from hiddifypanel.panel import hiddify, github_issue_generator
from sys import version as python_version
from platform import platform
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException

from apiflask import APIFlask,HTTPError,abort
def init_app(app:APIFlask):
    app.jinja_env.globals['ConfigEnum'] = ConfigEnum
    app.jinja_env.globals['DomainType'] = DomainType
    app.jinja_env.globals['UserMode'] = UserMode
    app.jinja_env.globals['hconfig'] = hconfig
    app.jinja_env.globals['g'] = g

    @app.errorhandler(Exception)
    def internal_server_error(e):
        # print(request.headers)
        last_version = hiddify.get_latest_release_version('hiddifypanel')  # TODO: add dev update check
        if "T" in hiddifypanel.__version__:
            has_update = False
        else:
            has_update = "dev" not in hiddifypanel.__version__ and f'{last_version}' != hiddifypanel.__version__


        if not request.accept_mimetypes.accept_html:
            if has_update:
                return jsonify({
                    'message':'This version of Hiddify Panel is outdated. please update it from admin area.',
                    }),500
            
            return jsonify({'message':str(e),
                            'detail':[f'{filename}:{line} {function}: {text}' for filename, line, function, text  in traceback.extract_tb(e.__traceback__)],
                            'version':hiddifypanel.__version__,
                            }),500
            
        
        trace = traceback.format_exc()

        # Create github issue link
        issue_link = generate_github_issue_link_for_500_error(e, trace)

        

        return render_template('500.html', error=e, trace=trace, has_update=has_update, last_version=last_version,issue_link= issue_link), 500
        
    @app.errorhandler(HTTPError)
    def internal_server_error(e):
        # print(request.headers)
        if not request.accept_mimetypes.accept_html:
            return app.error_callback(e)
        if e.status_code == 500:
            trace = traceback.format_exc()

            # Create github issue link
            issue_link = generate_github_issue_link_for_500_error(e, trace)

            last_version = hiddify.get_latest_release_version('hiddifypanel')  # TODO: add dev update check
            if "T" in hiddifypanel.__version__:
                has_update = False
            else:
                has_update = "dev" not in hiddifypanel.__version__ and f'{last_version}' != hiddifypanel.__version__

            return render_template('500.html', error=e, trace=trace, has_update=has_update, last_version=last_version,issue_link= issue_link), 500
        # if e.status_code in [400,401,403]:
        #     return render_template('access-denied.html',error=e), e.status_code

        return render_template('error.html', error=e), e.status_code

    def generate_github_issue_link(title, issue_body):
        opts = {
            "user": 'hiddify',
            "repo": 'Hiddify-Manager',
            "title": title,
            "body": issue_body,
        }
        issue_link = str(github_issue_generator.IssueUrl(opts).get_url())
        return issue_link

    @app.spec_processor
    def set_default_path_values(spec):
        for path in spec['paths'].values():
            for operation in path.values():
                if 'parameters' in operation:
                    for parameter in operation['parameters']:
                        if parameter['name'] == 'proxy_path':
                            parameter['schema'] = {'type': 'string', 'default': g.proxy_path}
                        # elif parameter['name'] == 'user_secret':
                        #     parameter['schema'] = {'type': 'string', 'default': g.user_uuid}
        return spec

    @app.url_defaults
    def add_proxy_path_user(endpoint, values):

        if 'user_secret' not in values and hasattr(g, 'user_uuid'):
            values['user_secret'] = f'{g.user_uuid}'
        if 'proxy_path' not in values:
            # values['proxy_path']=f'{g.proxy_path}'
            values['proxy_path'] = hconfig(ConfigEnum.proxy_path)

    @app.route("/<proxy_path>/videos/<file>")
    @app.doc(hide=True)
    def videos(file):
        print("file", file, app.config['HIDDIFY_CONFIG_PATH'] +
              '/hiddify-panel/videos/'+file)
        return send_from_directory(app.config['HIDDIFY_CONFIG_PATH']+'/hiddify-panel/videos/', file)
    # @app.template_filter()
    # def rel_datetime(value):
    #     diff=datetime.datetime.now()-value
    #     return format_timedelta(diff, add_direction=True, locale=hconfig(ConfigEnum.lang))

    @app.url_value_preprocessor
    def pull_secret_code(endpoint, values):
        # print("Y",endpoint, values)6
        # if values is None:
        #     return
        # if hiddifypanel.__release_date__ + datetime.timedelta(days=40) < datetime.datetime.now() or hiddifypanel.__release_date__ > datetime.datetime.now():
        #     abort(400, _('This version of hiddify panel is outdated. Please update it from admin area.'))
        g.user = None
        g.user_uuid = None
        g.is_admin = False

        if request.args.get('darkmode') != None:
            session['darkmode'] = request.args.get(
                'darkmode', '').lower() == 'true'
        g.darkmode = session.get('darkmode', False)
        import random
        g.install_pwa = random.random() <= 0.05
        if request.args.get('pwa') != None:
            session['pwa'] = request.args.get('pwa', '').lower() == 'true'
        g.pwa = session.get('pwa', False)

        g.user_agent = user_agents.parse(request.user_agent.string)
        
        if g.user_agent.is_bot:
            abort(400, "invalid")
        g.proxy_path = values.pop('proxy_path', None) if values else None

        if g.proxy_path != hconfig(ConfigEnum.proxy_path):
            if app.config['DEBUG']:
                abort(400, Markup(
                    f"Invalid Proxy Path <a href=/{hconfig(ConfigEnum.proxy_path)}/{get_super_admin_secret()}/admin>admin</a>"))
            abort(400, "Invalid Proxy Path")
        if endpoint == 'static' or endpoint == "videos":
            return
        tmp_secret = values.pop('user_secret', None) if values else None
        try:
            if tmp_secret:
                g.user_uuid = uuid.UUID(tmp_secret)
        except:
            # raise PermissionError("Invalid secret")
            abort(400, 'invalid user')
        g.admin = get_admin_user_db(tmp_secret)
        g.is_admin = g.admin is not None
        bare_path = request.path.replace(
            g.proxy_path, "").replace(tmp_secret, "").lower()
        if not g.is_admin:
            g.user = User.query.filter(User.uuid == f'{g.user_uuid}').first()
            if not g.user:
                abort(401, 'invalid user')
            if endpoint and ("admin" in endpoint or "api/v1" in endpoint):
                # raise PermissionError("Access Denied")
                abort(403, 'Access Denied')
            if "admin" in bare_path or "api/v1" in bare_path:
                abort(403, 'Access Denied')

        if hconfig(ConfigEnum.telegram_bot_token):
            import hiddifypanel.panel.commercial.telegrambot as telegrambot
            if (not telegrambot.bot) or (not telegrambot.bot.username):
                telegrambot.register_bot()
            g.bot = telegrambot.bot
        else:
            g.bot = None

        # print(g.user)

    def github_issue_details():
        details = {
            'hiddify_version': f'{hiddifypanel.__version__}',
            'python_version': f'{python_version}',
            'os_details': f'{platform()}',
            'user_agent': 'Unknown'
        }
        if hasattr(g, 'user_agent') and str(g.user_agent):
            details['user_agent'] = g.user_agent.ua_string
        return details

    def generate_github_issue_link_for_500_error(error, traceback, remove_sensetive_data=True, remove_unrelated_traceback_datails=True):

        def remove_sensetive_data_from_github_issue_link(issue_link):
            if hasattr(g, 'user_uuid') and g.user_uuid:
                issue_link.replace(f'{g.user_uuid}', '*******************')
            if hconfig(ConfigEnum.proxy_path) and hconfig(ConfigEnum.proxy_path):
                issue_link.replace(hconfig(ConfigEnum.proxy_path), '**********')

        def remove_unrelated_traceback_details(stacktrace: str):
            lines = stacktrace.splitlines()
            if len(lines) < 1:
                return ""

            output = ''
            skip_next_line = False
            for i, line in enumerate(lines):
                if i == 0:
                    output += line + '\n'
                    continue
                if skip_next_line == True:
                    skip_next_line = False
                    continue
                if line.strip().startswith('File'):
                    if 'hiddify' in line.lower():
                        output += line + '\n'
                        output += lines[i + 1] + '\n'
                    skip_next_line = True

            return output

        if remove_unrelated_traceback_datails:
            traceback = remove_unrelated_traceback_details(traceback)

        issue_details = github_issue_details()

        issue_body = render_template('github_issue_body.j2',issue_details=issue_details,error=error,traceback=traceback)

        # Create github issue link
        issue_link = generate_github_issue_link(f"Internal server error: {error.name if hasattr(error,'name') and error.name != None and error.name else 'Unknown'}", issue_body)

        if remove_sensetive_data:
            remove_sensetive_data_from_github_issue_link(issue_link)

        return issue_link

    def generate_github_issue_link_for_admin_sidebar():

        issue_body = render_template('github_issue_body.j2',issue_details=github_issue_details())

        # Create github issue link
        issue_link = generate_github_issue_link('Please fill the title properly', issue_body)
        return issue_link

    app.jinja_env.globals['generate_github_issue_link_for_admin_sidebar'] = generate_github_issue_link_for_admin_sidebar
