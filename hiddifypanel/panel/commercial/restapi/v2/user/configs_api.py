from urllib.parse import urlparse
from flask import g, request
from flask import current_app as app
from flask.views import MethodView
from hiddifypanel.models.config import  hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.panel import hiddify
from apiflask import Schema
from apiflask.fields import String
from hiddifypanel.panel.user.user import get_common_data
from hiddifypanel.panel.user import link_maker


class ConfigSchema(Schema):
    name = String(required=True)
    domain = String(required=True)
    link = String(required=True)
    protocol = String(required=True)
    transport = String(required=True)
    security = String(required=True)
    type = String(required=True)

class AllConfigsAPI(MethodView):
    decorators = [hiddify.user_auth]

    @app.output(ConfigSchema(many=True))
    def get(self):
        def create_item(name, type, domain, protocol, transport, security, link):
            dto = ConfigSchema()
            dto.name = name
            dto.type = type
            dto.domain = domain
            dto.protocol = protocol
            dto.transport = transport
            dto.security = security
            dto.link = link
            return dto

        items = []
        base_url = f"https://{urlparse(request.base_url).hostname}/{g.proxy_path}/{g.user_uuid}/"
        c = get_common_data(g.user_uuid, 'new')

        # Add Auto
        items.append(
            create_item(
                "Auto", "All", "All", "All", "All", "All",
                f"{base_url}sub/?asn={c['asn']}")
        )

        # Add Full Singbox
        items.append(
            create_item(
                "Full Singbox", "All", "All", "All", "All", "All",
                f"{base_url}full-singbox.json?asn={c['asn']}"
            )
        )

        # Add Clash Meta
        items.append(
            create_item(
                "Clash Meta", "All", "All", "All", "All", "All",
                f"clashmeta://install-config?url={base_url}clash/meta/all.yml&name=mnormal_{c['db_domain'].alias or c['db_domain'].domain}-{c['asn']}-{c['mode']}&asn={c['asn']}&mode={c['mode']}"
            )
        )

        # Add Clash
        items.append(
            create_item(
                "Clash", "All", "All", "Except VLess", "All", "All",
                f"clash://install-config?url={base_url}clash/all.yml&name=new_normal_{c['db_domain'].alias or c['db_domain'].domain}-{c['asn']}-{c['mode']}&asn={c['asn']}&mode={c['mode']}"
            )
        )

        # Add Singbox: SSh
        if hconfig(ConfigEnum.ssh_server_enable):
            items.append(
                create_item(
                    "Singbox: SSH", "SSH", "SSH", "SSH", "SSH", "SSH",
                    f"{base_url}singbox.json?name={c['db_domain'].alias or c['db_domain'].domain}-{c['asn']}&asn={c['asn']}&mode={c['mode']}"
                )
            )

        # Add Subscription link
        items.append(
            create_item(
                "Subscription link", "All", "All", "All", "All", "All",
                f"{base_url}all.txt?name={c['db_domain'].alias or c['db_domain'].domain}-{c['asn']}&asn={c['asn']}&mode={c['mode']}"
            )
        )

        # Add Subscription link base64
        items.append(
            create_item(
                "Subscription link b64", "All", "All", "All", "All", "All",
                f"{base_url}all.txt?name=new_link_{c['db_domain'].alias or c['db_domain'].domain}-{c['asn']}-{c['mode']}&asn={c['asn']}&mode={c['mode']}&base64=True"
            )
        )

        for pinfo in link_maker.get_all_validated_proxies(c['domains']):
            items.append(
                create_item(
                    pinfo["name"].replace("_", " "),
                    f"{'Auto ' if pinfo['dbdomain'].has_auto_ip else ''}{pinfo['mode']}",
                    pinfo['server'],
                    pinfo['proto'],
                    pinfo['transport'],
                    pinfo['l3'],
                    f"{link_maker.to_link(pinfo)}"
                )
            )

        return items

