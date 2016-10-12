#!/usr/bin/env python

from setuptools import setup

setup(
    name = "artemis",
    version = __import__("artemis").__version__,
    author = "Dmitriy Morozov",
    author_email = "dmitriy@mrzv.org",
    description = "Issue tracking for mercurial or git",
    url = "https://github.com/mrzv/artemis",
    py_modules=["artemis"],
    scripts=["git-artemis"],
    install_requires=["mercurial"],
    zip_safe = False,
    license="BSD",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Software Development :: Version Control",
    ]
)
