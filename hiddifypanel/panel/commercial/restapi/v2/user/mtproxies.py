from flask.views import MethodView
from apiflask import Schema
from flask import g
from flask import current_app as app
from apiflask.fields import String

from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.domain import DomainType

from hiddifypanel.panel.user.user import get_common_data
from hiddifypanel.panel import hiddify

class MtproxySchema(Schema):
    link = String(required=True)
    title = String(required=True)

class MTProxiesAPI(MethodView):
    decorators = [hiddify.user_auth]

    @app.output(MtproxySchema(many=True))
    def get(self):
        # get domains
        c = get_common_data(g.user_uuid, 'new')
        dtos = []
        # TODO: Remove duplicated domains mapped to a same ipv4 and v6
        for d in c['domains']:
            if d.mode not in [DomainType.direct, DomainType.relay]:
                continue
            hexuuid = hconfig(ConfigEnum.shared_secret, d.child_id).replace('-', '')
            telegram_faketls_domain_hex = hconfig(ConfigEnum.telegram_fakedomain, d.child_id).encode('utf-8').hex()
            server_link = f'tg://proxy?server={d.domain}&port=443&secret=ee{hexuuid}{telegram_faketls_domain_hex}'
            dto = MtproxySchema()
            dto.title = d.alias or d.domain
            dto.link = server_link
            dtos.append(dto)
        return dtos