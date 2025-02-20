from apiflask import APIBlueprint

bp = APIBlueprint("api_user", __name__, url_prefix="/<proxy_path>/<user_secret>/api/v2/user/", enable_openapi=True)


def init_app(app):
    with app.app_context():
        from .info_api import InfoAPI
        from .apps_api import AppAPI
        from .mtproxies import MTProxiesAPI
        from .configs_api import AllConfigsAPI
        from .short_api import ShortAPI
        from .apps_api import AppAPI
        
        bp.add_url_rule("/me/", view_func=InfoAPI)
        bp.add_url_rule("/mtproxies/", view_func=MTProxiesAPI)
        bp.add_url_rule("/all-configs/", view_func=AllConfigsAPI)
        bp.add_url_rule("/short/", view_func=ShortAPI)
        bp.add_url_rule('/apps/',view_func=AppAPI)

    app.register_blueprint(bp)
