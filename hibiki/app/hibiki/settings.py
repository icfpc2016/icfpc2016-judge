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

import gflags

from hibiki import misc_util

FLAGS = gflags.FLAGS

gflags.DEFINE_string(
    'admin_username', 'admin',
    'Admin username.')
gflags.DEFINE_string(
    'admin_password', None,
    'Admin password.')
gflags.DEFINE_integer(
    'contest_start_time', None,
    'Timestamp when the contest starts.')
gflags.DEFINE_integer(
    'contest_first_publish_time', None,
    'Timestamp when the first group of team problems are published.')
gflags.DEFINE_integer(
    'contest_freeze_time', None,
    'Timestamp when the leaderboard is frozen.')
gflags.DEFINE_integer(
    'contest_last_publish_time', None,
    'Timestamp when the last group of team problems are published.')
gflags.DEFINE_integer(
    'contest_end_time', None,
    'Timestamp when the contest finishes.')
gflags.DEFINE_integer(
    'contest_primary_snapshot_interval', None,
    'Interval of public contest snapshots and problem publish in seconds.')
gflags.DEFINE_integer(
    'contest_secondary_snapshot_interval', None,
    'Interval of secondary snapshots.')
gflags.DEFINE_float(
    'api_rate_limit_request_interval', 0.9,
    'Minimum required time between API requests in seconds.')
gflags.DEFINE_integer(
    'api_rate_limit_window_size', None,
    'Window size of API rate limit in seconds.')
gflags.DEFINE_integer(
    'api_rate_limit_submissions_in_window', None,
    'Permitted submissions in API rate limit window.')
gflags.DEFINE_integer(
    'api_rate_limit_blob_lookups_in_window', None,
    'Permitted blob lookups in API rate limit window.')
gflags.DEFINE_float(
    'web_rate_limit_requests_per_minute', 20,
    'Permitted web RPS.')
gflags.DEFINE_integer(
    'web_rate_limit_allowed_burst_requests', 10,
    'Permitted web request burst requests.')
gflags.DEFINE_bool(
    'enable_load_test_hacks', False,
    'Enables special hacks for load testing.')
gflags.MarkFlagAsRequired('contest_start_time')
gflags.MarkFlagAsRequired('contest_first_publish_time')
gflags.MarkFlagAsRequired('contest_freeze_time')
gflags.MarkFlagAsRequired('contest_last_publish_time')
gflags.MarkFlagAsRequired('contest_end_time')
gflags.MarkFlagAsRequired('contest_primary_snapshot_interval')
gflags.MarkFlagAsRequired('contest_secondary_snapshot_interval')
gflags.MarkFlagAsRequired('api_rate_limit_window_size')
gflags.MarkFlagAsRequired('api_rate_limit_submissions_in_window')
gflags.MarkFlagAsRequired('api_rate_limit_blob_lookups_in_window')
gflags.MarkFlagAsRequired('admin_password')


_CONTEST_TIME_FLAGS = (
    'contest_start_time',
    'contest_first_publish_time',
    'contest_freeze_time',
    'contest_last_publish_time',
    'contest_end_time',
)


def validate():
    """Validates settings are consistent.

    Raises:
        ValueError: If settings are inconsitent.
    """
    for flag in _CONTEST_TIME_FLAGS:
        delta = getattr(FLAGS, flag) - FLAGS.contest_start_time
        if delta % FLAGS.contest_primary_snapshot_interval != 0:
            raise ValueError(
                '%s is not aligned to contest_primary_snapshot_interval' % flag)
    if (FLAGS.contest_primary_snapshot_interval %
            FLAGS.contest_secondary_snapshot_interval != 0):
        raise ValueError(
            'contest_primary_snapshot_interval must be multiples of '
            'contest_secondary_snapshot_interval')
    contest_length = FLAGS.contest_end_time - FLAGS.contest_start_time
    if contest_length % FLAGS.api_rate_limit_window_size != 0:
        raise ValueError('api_rate_limit_window_size is not aligned to contest length')


def get_admin_credential():
    """Returns the admin credential.

    Returns:
        (username, password)
    """
    return (FLAGS.admin_username, FLAGS.admin_password)


def has_contest_started():
    """Returns if the contest has started.

    Args:
        A boolean.
    """
    return misc_util.time() >= FLAGS.contest_start_time


def has_contest_finished():
    """Returns if the contest has finished.

    Args:
        A boolean.
    """
    return misc_util.time() >= FLAGS.contest_end_time


def is_contest_running():
    """Returns if the contest is running.

    Args:
        A boolean.
    """
    return FLAGS.contest_start_time <= misc_util.time() < FLAGS.contest_end_time


def get_last_primary_snapshot_time():
    """Returns the last primary snapshot timestamp.

    This does not look into database, so snapshot might not be available yet.

    Returns:
        An integer of the last primary snapshot timestamp.
    """
    return misc_util.align_timestamp(
        misc_util.time(), FLAGS.contest_start_time,
        FLAGS.contest_primary_snapshot_interval)


def get_last_secondary_snapshot_time():
    """Returns the last secondary snapshot timestamp.

    This does not look into database, so snapshot might not be available yet.

    Returns:
        An integer of the last secondary snapshot timestamp.
    """
    return misc_util.align_timestamp(
        misc_util.time(), FLAGS.contest_start_time,
        FLAGS.contest_secondary_snapshot_interval)


def is_primary_snapshot_time(timestamp):
    """Checks if the given timestamp is a primary snapshot time.

    Args:
        timestamp: An integer timestamp.

    Returns:
        True if the timestamp if a primary snapshot time, otherwise False.
    """
    assert isinstance(timestamp, (int, long))
    delta = timestamp - FLAGS.contest_start_time
    return delta % FLAGS.contest_primary_snapshot_interval == 0


def is_secondary_snapshot_time(timestamp):
    """Checks if the given timestamp is a secondary snapshot time.

    Args:
        timestamp: An integer timestamp.

    Returns:
        True if the timestamp if a secondary snapshot time, otherwise False.
    """
    assert isinstance(timestamp, (int, long))
    delta = timestamp - FLAGS.contest_start_time
    return delta % FLAGS.contest_secondary_snapshot_interval == 0


def is_valid_publish_time(timestamp):
    """Checks if the given timestamp is a valid publish time.

    Args:
        timestamp: An integer timestamp.

    Returns:
        True if the timestamp if a valid publish time, otherwise False.
    """
    assert isinstance(timestamp, (int, long))
    return (is_primary_snapshot_time(timestamp) and
            FLAGS.contest_first_publish_time <= timestamp <=
            FLAGS.contest_last_publish_time)


def is_public_problem_ranking_snapshot_time(timestamp):
    """Checks if the given timestamp is a public problem ranking snapshot time.

    Args:
        timestamp: An integer timestamp.

    Returns:
        True if the timestamp if a public problem ranking snapshot time,
        otherwise False.
    """
    assert isinstance(timestamp, (int, long))
    return (is_primary_snapshot_time(timestamp) and
            timestamp <= FLAGS.contest_end_time)


def is_public_leaderboard_snapshot_time(timestamp):
    """Checks if the given timestamp is a public leaderboard snapshot time.

    Args:
        timestamp: An integer timestamp.

    Returns:
        True if the timestamp if a public leaderboard snapshot time,
        otherwise False.
    """
    assert isinstance(timestamp, (int, long))
    return (is_primary_snapshot_time(timestamp) and
            timestamp <= FLAGS.contest_freeze_time)


def get_next_publish_time():
    """Returns the next problem publish timestamp.

    Returns:
        An integer of the next problem publish timestamp.

    Raises:
        ValueError: If all problem publishes have finished.
    """
    now = misc_util.time()
    if now < FLAGS.contest_first_publish_time:
        return FLAGS.contest_first_publish_time
    next_primary_snapshot_time = (
        misc_util.align_timestamp(
            now, FLAGS.contest_first_publish_time,
            FLAGS.contest_primary_snapshot_interval) +
        FLAGS.contest_primary_snapshot_interval)
    if next_primary_snapshot_time > FLAGS.contest_last_publish_time:
        raise ValueError('All problem publishes have finished.')
    return next_primary_snapshot_time
