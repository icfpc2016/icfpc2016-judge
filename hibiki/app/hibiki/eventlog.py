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

import contextlib
import logging
import traceback

import fluent.event
import fluent.sender
import gflags

from hibiki import misc_util

FLAGS = gflags.FLAGS

gflags.DEFINE_bool(
    'enable_eventlog', False,
    'Enable eventlog reporting.')


def connect():
    if not FLAGS.enable_eventlog:
        return
    fluent.sender.setup('hibiki')


def emit(name, data):
    """Emits an event log.

    Args:
        name: Name of the event.
        data: Dictionary of the event data.
    """
    assert isinstance(name, str)
    assert isinstance(data, dict)
    if not FLAGS.enable_eventlog:
        return
    fluent.event.Event(name, data)


def exception(msg, *args):
    if args:
        msg = msg % args
    logging.exception(msg)
    emit(
        'exception',
        {
            'message': msg,
            'traceback': traceback.format_exc(),
        })


@contextlib.contextmanager
def record_time(name, data={}):
    data = data.copy()
    start_time = misc_util.time()
    yield data
    processing_time = misc_util.time() - start_time
    data['processing_time'] = processing_time
    emit(name, data)
