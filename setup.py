import os

from setuptools import setup, find_packages

README = ""
CHANGES = ""

requires = [
    "cherubplay",
    "tornado",
    "tornado-redis",
]

setup(
	name="cherubplay_live",
    packages=find_packages(),
    zip_safe=False,
    install_requires=requires,
    entry_points="""\
    [console_scripts]
    cherubplay_search = cherubplay_live.search:main
    """,
)
