import os
import sys
import transaction

from datetime import datetime, timedelta
from sqlalchemy import and_, engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from pyramid.scripts.common import parse_vars

from cherubplay.models import (
    Session,
    Base,
    Request,
    User,
)


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    Session.configure(bind=engine)

    Session.query(Request).filter(and_(
        Request.status == "posted",
        Request.user_id.in_(
            Session.query(User.id)
            .filter(User.last_online < datetime.now() - timedelta(7))
        ),
    )).update({"status": "draft"}, synchronize_session=False),
    transaction.commit()

