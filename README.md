pypitools
=========

Collection of useful tools to query PyPI data

Setup
-----

Put this directory into your search path

- Bash: Edit your ~/.bash\_profile:

    PATH = $PATH:~/pypitools
    export PATH

- Fish: Edit your ~/.config/fish/config.fish:

    set -x PATH ~/pypitools $PATH

Run `pypipkglist update` once

Usage
-----

pypipkglist.py queries a locally cached PyPI package list.
pypiupdate.py checks for updates to your (virtualenv) packages.
pypiautocompleter.py outputs pypipkglist.py package names only. It's quicker than the full-featured script and therefore suitable for autocompletion.
