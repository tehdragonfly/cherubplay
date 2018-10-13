Config examples
===============

Supervisor config
-----------------

Cherubplay is currently run using [Supervisor](http://supervisord.org/). Suggested configuration:

### Main processes

    [program:cherubplay]
    command = /path/to/virtualenv/bin/uwsgi --ini /conf/uwsgi.ini
    autostart = false
    user = cherubplay

    [program:cherubplay_search]
    command = /path/to/virtualenv/bin/cherubplay_search /conf/cherubplay.ini
    autostart = false
    user = cherubplay

    [program:cherubplay_chat]
    command = /path/to/virtualenv/bin/cherubplay_chat /conf/cherubplay.ini
    autostart = false
    user = cherubplay

### Databases

    [program:cherubplay_login]
    command = redis-server /conf/redis_login.conf
    autostart = false
    user = redis

    [program:cherubplay_pubsub]
    command = redis-server /conf/redis_pubsub.conf
    autostart = false
    user = redis

### Task runners

    [program:cherubplay_celerybeat]
    command = /path/to/virtualenv/bin/celery beat -A pyramid_celery.celery_app --ini /conf/cherubplay.ini -l DEBUG
    autostart = false
    user = cherubplay
