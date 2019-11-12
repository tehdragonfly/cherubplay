cherubplay README
==================

Project structure
-----------------

* `cherubplay/` - contains the main Pyramid application.
  * `scripts/` - various scripts.
    * `initializedb.py` - script for creating database tables. Installed as `initialize_cherubplay_db`.
  * `tasks/` - Celery tasks for async work.
* `cherubplay_live/` - contains Tornado applications for WebSockets.
  * `chat.py` - application for live updates in chats. Installed as `cherubplay_chat`.
  * `search.py` - application for prompts on the front page. Installed as `cherubplay_search`.

Setting up a dev environment
----------------------------

Install the requirements:

    pip install -r requirements.txt

Install the Cherubplay package:

    pip install -e .

`sample.ini` contains an example Paste configuration file. Copy this to `development.ini` and fill in the details.

Create the database tables:

    initialize_cherubplay_db development.ini

Run the Pyramid application:

    pserve development.ini --reload

Run the search handler:

    cherubplay_search development.ini

Run the chat handler:

    cherubplay_chat development.ini

Run a Celery worker:

    celery worker -A pyramid_celery.celery_app --ini development.ini -l DEBUG -Q celery,export,cleanup

Note that using different Celery workers for the different queues is recommended in production. See `CONFIG.md` for more details.
