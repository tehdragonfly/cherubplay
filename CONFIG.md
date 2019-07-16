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

Cherubplay uses two Celery workers: one for quick tasks like triggering push
notifications and another for longer tasks like exporting chats and cleanup
tasks. Celery recommends doing this so that quick tasks don't get stuck behind
slower ones.

When you're running multiple Celery processes on the same host you need to
specify worker names manually with `-n` to disambiguate them.

    [program:cherubplay_celery_main]
    command = /path/to/virtualenv/bin/celery worker -A pyramid_celery.celery_app --ini /conf/cherubplay.ini -l DEBUG -c 4 -n "main@%h"
    autostart = false
    user = cherubplay

    [program:cherubplay_celery_export]
    command = /path/to/virtualenv/bin/celery worker -A pyramid_celery.celery_app --ini /conf/cherubplay.ini -l DEBUG -c 4 -n "export@%h" -Q export,cleanup
    autostart = false
    user = cherubplay

The beat process triggers scheduled tasks.

    [program:cherubplay_celerybeat]
    command = /path/to/virtualenv/bin/celery beat -A pyramid_celery.celery_app --ini /conf/cherubplay.ini -l DEBUG
    autostart = false
    user = cherubplay

Nginx config
------------

### Redirect for the bare domain without HTTPS

    server {
        listen 80;
        listen [::]:80;
        server_name cherubplay.co.uk;
        return 301 https://cherubplay.co.uk$request_uri;
    }

### Redirect for the bare domain with HTTPS

    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name cherubplay.co.uk;
        ssl_certificate /path/to/letsencrypt/cherubplay.co.uk/fullchain.pem;
        ssl_certificate_key /path/to/letsencrypt/cherubplay.co.uk/privkey.pem;
        add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";
        return 301 https://www.cherubplay.co.uk$request_uri;
    }

These redirects cause a two-step redirect chain:

1. `http://cherubplay.co.uk/` -> `https://cherubplay.co.uk/`
2. `https://cherubplay.co.uk/` -> `https://www.cherubplay.co.uk/`

The first step is needed so the browser recieves the HSTS header for the base domain.

### Redirect for www without HTTPS

    server {
        listen 80;
        listen [::]:80;
        server_name www.cherubplay.co.uk;
        return 301 https://www.cherubplay.co.uk$request_uri;
    }

### Actual domain

    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name www.cherubplay.co.uk;
        charset utf-8;
        ssl_certificate /path/to/letsencrypt/www.cherubplay.co.uk/fullchain.pem;
        ssl_certificate_key /path/to/letsencrypt/www.cherubplay.co.uk/privkey.pem;
        add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";
        # The service worker is served from /static/ but needs to run on the whole domain.
        add_header Service-Worker-Allowed /;
        location / {
            # Uses UWSGI to communicate with the main application server
            uwsgi_pass unix:///tmp/cherubplay_uwsgi.sock;
            include uwsgi_params;
            uwsgi_param SCRIPT_NAME "";
        }
        location /search/ {
            # Proxy to the search WebSocket server
            proxy_pass http://unix:/tmp/cherubplay_search.sock:/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 20;
            proxy_buffering off;
        }
        location /live/ {
            # Proxy to the chat WebSocket server
            proxy_pass http://unix:/tmp/cherubplay_chat.sock:/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 20;
            proxy_buffering off;
        }
        location /static/ {
            # Static files
            root /path/to/virtualenv/cherubplay/cherubplay/;
        }
        location /export/ {
            # Storage for exported chats
            root /path/to/export/;
        }
        location /.well-known/acme-challenge/ {
            # ACME challenge directory for certificate renewal
            root /usr/share/nginx/html/acme/;
        }
    }