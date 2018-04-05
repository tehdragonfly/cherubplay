cherubplay README
==================

Setting up a dev environment
----------------------------

Install the requirements:

    pip install -r requirements.txt

Install the Cherubplay package:

    pip install -e .

Create the database tables:

    initialize_cherubplay_db development.ini

Run the Pyramid application:

    pserve development.ini --reload

Run the search handler:

    cherubplay_search development.ini

Run the chat handler:

    cherubplay_chat development.ini

