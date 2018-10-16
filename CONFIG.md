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

Nginx config
------------

    server {
        listen 80;
        listen [::]:80;
        server_name cherubplay.co.uk;
        return 301 https://cherubplay.co.uk$request_uri;
    }

    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name cherubplay.co.uk;
        ssl_certificate /path/to/letsencrypt/cherubplay.co.uk/fullchain.pem;
        ssl_certificate_key /path/to/letsencrypt/cherubplay.co.uk/privkey.pem;
        add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";
        return 301 https://www.cherubplay.co.uk$request_uri;
    }

    server {
        listen 80;
        listen [::]:80;
        server_name www.cherubplay.co.uk;
        return 301 https://www.cherubplay.co.uk$request_uri;
    }

    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name www.cherubplay.co.uk lurantis.cherubplay.co.uk;
        charset utf-8;
        ssl_certificate /path/to/letsencrypt/www.cherubplay.co.uk/fullchain.pem;
        ssl_certificate_key /path/to/letsencrypt/www.cherubplay.co.uk/privkey.pem;
        add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";
        add_header Service-Worker-Allowed /;
        location / {
            uwsgi_pass unix:///tmp/cherubplay_uwsgi.sock;
            include uwsgi_params;
            uwsgi_param SCRIPT_NAME "";
        }
        location /search/ {
            proxy_pass http://unix:/tmp/cherubplay_search.sock:/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 20;
            proxy_buffering off;
        }
        location /live/ {
            proxy_pass http://unix:/tmp/cherubplay_chat.sock:/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 20;
            proxy_buffering off;
        }
        location /static/ {
            root /path/to/virtualenv/cherubplay/cherubplay/;
        }
        location /export/ {
            root /path/to/export/;
        }
        location /.well-known/acme-challenge/ {
            root /usr/share/nginx/html/acme/;
        }
    }