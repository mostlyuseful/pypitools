#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pkgtools.pypi import PyPIJson
import pip
import progressbar
from Queue import Queue
from threading import Thread

def worker():
    while True:
        pkg = q.get()
        try:
            remote = PyPIJson(pkg.project_name).retrieve()
            remote_version = remote['info']['version']
            if remote_version != pkg.version:
                outdated.append((pkg,remote_version))
        except Exception as e:
            print "Error occurred:"
            print e
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

    pkg_list = pip.get_installed_distributions()
    progress = progressbar.ProgressBar(widgets=[progressbar.SimpleProgress(), ' ', progressbar.Bar(), ' ', progressbar.ETA()], maxval=len(pkg_list)).start()
    for pkg in pkg_list:
        q.put(pkg)
    q.join()
    progress.finish()

    if outdated:
        print "Run the following command to update all outdated packages:"
        print "pip install -U " + " ".join(["%s==%s"%(pkg.project_name,version) for (pkg,version) in outdated])
    else:
        print "Everything is up to date."
