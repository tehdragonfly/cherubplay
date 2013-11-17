from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    Session,
    Base,
)


def main(global_config, **settings):

    engine = engine_from_config(settings, 'sqlalchemy.')
    Session.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')

    config.add_route('sign_up', '/sign-up/')
    config.add_route('log_in', '/log-in/')
    config.add_route('log_out', '/log-out/')

    config.add_route('chat_list', '/chats/')
    config.add_route('chat_list_archive', '/chats/archive/')

    config.add_route('chat', '/chats/{url}/')
    config.add_route('chat_archive', '/chats/url}/archive/')

    config.add_route('account', '/account/')

    config.scan()
    return config.make_wsgi_app()

