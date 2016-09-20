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

import logging
import logging.handlers
import os
import sys

import bottle
import gflags

from hibiki import eventlog
from hibiki import settings

FLAGS = gflags.FLAGS

gflags.DEFINE_bool('logtostderr', True, 'Log to stderr.')
gflags.DEFINE_bool('logtosyslog', False, 'Log to syslog.')
gflags.DEFINE_bool('debug', False, 'Enable debug.')


def _setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)-15s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    if FLAGS.logtostderr:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    if FLAGS.logtosyslog:
        handler = logging.handlers.SysLogHandler('/dev/log')
        handler.setFormatter(formatter)
        root.addHandler(handler)
    # Suppress apscheduler's verbose logging.
    logging.getLogger('apscheduler.executors').setLevel(logging.WARNING)


def _setup_bottle():
    bottle.TEMPLATE_PATH = [os.path.join(os.path.dirname(__file__), 'templates')]
    bottle.BaseRequest.MEMFILE_MAX = 8 * 1024 * 1024


def setup_common():
    FLAGS(sys.argv)
    _setup_logging()
    settings.validate()
    eventlog.connect()
    _setup_bottle()
    if FLAGS.debug:
        bottle.debug()
