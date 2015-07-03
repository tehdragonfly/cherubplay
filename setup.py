import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.txt")) as f:
    README = f.read()
with open(os.path.join(here, "CHANGES.txt")) as f:
    CHANGES = f.read()

setup(name="cherubplay",
      version="0.0",
      description="cherubplay",
      long_description=README + "\n\n" + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author="",
      author_email="",
      url="",
      keywords="web wsgi bfg pylons pyramid",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite="cherubplay",
      # Requirements are in requirements.txt
      install_requires=[],
      entry_points="""\
      [paste.app_factory]
      main = cherubplay:main
      [console_scripts]
      initialize_cherubplay_db = cherubplay.scripts.initializedb:main
      cherubplay_search = cherubplay_live.search:main
      cherubplay_chat = cherubplay_live.chat:main
      """,
      )
