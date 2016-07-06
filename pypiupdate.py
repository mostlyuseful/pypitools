#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from pkgtools.pypi import PyPIJson
import pip
import progressbar
import traceback
from threading import Thread

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
        done.append(pkg)
        progress.update(len(done))
        q.task_done()

if __name__=='__main__':
    
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

    if outdated:
        print("Run the following command to update all outdated packages:")
        #print("pip install -U " + " ".join(["%s==%s"%(pkg.project_name,version) for (pkg,version) in outdated]))
        print("pip install -U " + " ".join(sorted(pkg.project_name for (pkg,version) in outdated)))
    else:
        print("Everything is up to date.")
