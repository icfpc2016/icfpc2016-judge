# Copyright 2016 ICFP Programming Contest 2016 Organizers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import os
import signal
import sys

import bottle
import gflags

import subprocess32 as subprocess

from hibiki import cron_flags as _cron_flags_import_only
from hibiki import handler as _handler_import_only
from hibiki import model
from hibiki import setup

FLAGS = gflags.FLAGS

gflags.DEFINE_integer('port', 8080, 'Port to listen on.')
gflags.DEFINE_bool('run_cron_in_background', False, 'Run cron in background.')


def _run_cron_in_background():
    if os.environ.get('BOTTLE_CHILD'):
        return
    proc = subprocess.Popen(
        [sys.executable, '-m', 'hibiki.cron_main'] + sys.argv[1:],
        preexec_fn=os.setpgrp)
    def kill_cron():
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait()
    atexit.register(kill_cron)


def main():
    setup.setup_common()
    model.connect()
    if FLAGS.run_cron_in_background:
        _run_cron_in_background()
    bottle.run(
        # wsgiref is unstable with reloader.
        # See: https://github.com/bottlepy/bottle/issues/155
        server='paste',
        port=FLAGS.port,
        host='0.0.0.0',
        reloader=True)


if __name__ == '__main__':
    sys.exit(main())
