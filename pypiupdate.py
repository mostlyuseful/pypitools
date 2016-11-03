#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import logging
LOGGING_FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

from pkgtools.pypi import PyPIJson
import pip
import progressbar
import traceback
import click
from threading import Thread


import pip.commands.install

def install_distributions(distributions, args=None):
    """From http://threebean.org/blog/2011/06/06/installing-from-pip-inside-python-or-a-simple-pip-api/
    """
    command = pip.commands.install.InstallCommand()
    opts, args = command.parser.parse_args(args)
    # TBD, why do we have to run the next part here twice before actual install
    requirement_set = command.run(opts, distributions)
    requirement_set = command.run(opts, distributions)
    requirement_set.install(opts)

try:
    # Python 2
    from Queue import Queue
except ImportError:
    # Python 3
    from queue import Queue

def worker():
    while True:
        pkg = q.get()
        try:
            remote = PyPIJson(pkg.project_name).retrieve()
            remote_version = remote['info']['version']
            if remote_version != pkg.version:
                outdated.append((pkg,remote_version))
        except Exception as e:
            print("""Error occurred while checking package "{0}":""".format(pkg))
            print(traceback.format_exc())
            try:
                attrs = vars(e)
                print('\n'.join(".{0} == {1}".format(key,val) for key,val in attrs.items()))
            except: pass
        done.append(pkg)
        progress.update(len(done))
        q.task_done()


def get_outdated():
    global progress
    global q
    global done
    global outdated
    
    outdated = []
    progress = None
    done = []
    
    # Start up worker pool
    q = Queue()
    # Ten concurrent connections are alright, I think.
    num_worker_threads = 10
    for i in range(num_worker_threads):
        t = Thread(target=worker)
        t.daemon = True
        t.start()

    only_local_packages = False
    pkg_list = pip.get_installed_distributions(local_only=only_local_packages)
    progress = progressbar.ProgressBar(widgets=[progressbar.SimpleProgress(), ' ', progressbar.Bar(), ' ', progressbar.ETA()], maxval=len(pkg_list)).start()
    for pkg in pkg_list:
        q.put(pkg)
    q.join()
    progress.finish()
    return outdated

def update_packages(pkg_list):
    for pkg in pkg_list:
        try:
            print("Updating {0}".format(pkg))
            install_distributions([pkg], ['-U','-v'])
            print("OK: Updated {0}".format(pkg))
        except Exception as e:
            print("""Error occurred while updating package "{0}":""".format(pkg))
            print(traceback.format_exc())

@click.command()
@click.option('--update/--no-update', default=False, help='Update or list only')
def main(update):
    outdated = get_outdated()

    if outdated:
        if update:
            update_packages(sorted(pkg.project_name for (pkg,version) in outdated))
        else:
            print("Run the following command to update all outdated packages:")
            print("pip install -U " + " ".join(sorted(pkg.project_name for (pkg,version) in outdated)))
    else:
        print("Everything is up to date.")

if __name__=='__main__':
    main()
