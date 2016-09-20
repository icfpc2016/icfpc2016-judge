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

import binascii
import datetime
import math
import os
import random
import time as time_lib

import bottle
import gflags

FLAGS = gflags.FLAGS

gflags.DEFINE_bool(
    'allow_override_time_for_testing', False,
    'Allows overriding current time by X-Override-Time: header.')

# List of characters that may appear in generated passwords.
_PASSWORD_CHARS = '23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghkmnpqrstuvwxyz'


def generate_random_id(length):
    """Generates a random ID.

    Args:
        length: Length of a generated random ID. Must be an even number.

    Returns:
        Generated random ID string.
    """
    assert length % 2 == 0
    return binascii.hexlify(os.urandom(length / 2))


def generate_password():
    """Generates a random password.

    Returns:
        Generated random password string.
    """
    return ''.join(random.choice(_PASSWORD_CHARS) for _ in xrange(12))


def format_timestamp(ts):
    """Formats a timestamp into a string.

    Args:
        ts: Timestamp, the number of seconds from UNIX epoch.

    Returns:
        A formatted string.
    """
    dt = datetime.datetime.utcfromtimestamp(ts)
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')


def align_timestamp(timestamp, base_timestamp, interval):
    """Aligns |timestamp| to |base_timestamp| plus multiples of |interval|.

    Args:
        timestamp: Timestamp.
        base_timestamp: Timestamp.
        interval: Alignment interval in seconds.
    """
    assert isinstance(base_timestamp, (int, long))
    assert isinstance(interval, (int, long))
    real_delta = timestamp - base_timestamp
    aligned_delta = int(math.floor(real_delta / interval)) * interval
    return base_timestamp + aligned_delta


def load_testdata(name):
    """Loads a test data.

    Args:
        name: Filename.

    Returns:
        A str.
    """
    with open(os.path.join(os.path.dirname(__file__), 'testdata', name)) as f:
        return f.read()


def time():
    """Returns the current time.

    Similar as time.time(), but can be overridden for testing.

    Returns:
        Timestamp.
    """
    if FLAGS.allow_override_time_for_testing:
        override_time = bottle.request.headers.get('X-Override-Time')
        if override_time:
            return float(override_time)
    return time_lib.time()
