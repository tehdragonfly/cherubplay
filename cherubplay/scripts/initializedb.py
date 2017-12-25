import os
import sys

from pyramid.paster import get_appsettings, setup_logging
from pyramid.scripts.common import parse_vars

from cherubplay.models import Base, get_sessionmaker


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
    sm = get_sessionmaker(get_appsettings(config_uri, options=options))
    db = sm()
    Base.metadata.create_all(db.get_bind())
