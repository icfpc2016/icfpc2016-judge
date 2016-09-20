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

import gflags

from hibiki import cron_flags as _cron_flags_import_only
from hibiki import eventlog
from hibiki import model
from hibiki import settings

FLAGS = gflags.FLAGS


def _make_snapshot(snapshot_time):
    assert settings.is_secondary_snapshot_time(snapshot_time)
    #logging.info('snapshot job start: snapshot_time=%d', snapshot_time)
    with eventlog.record_time('cron', {'snapshot_time': snapshot_time}):
        model.update_problem_ranking_snapshots(snapshot_time)
        model.update_leaderboard_snapshot(snapshot_time)
        if settings.is_primary_snapshot_time(snapshot_time):
            model.update_public_contest_snapshot(snapshot_time)
    #logging.info('snapshot job success: snapshot_time=%d', snapshot_time)


def snapshot_job():
    try:
        model.publish_scheduled_problems()
        primary_snapshot_time = settings.get_last_primary_snapshot_time()
        if model.lock_snapshot_cron_job(primary_snapshot_time):
            _make_snapshot(primary_snapshot_time)
        secondary_snapshot_time = settings.get_last_secondary_snapshot_time()
        if model.lock_snapshot_cron_job(secondary_snapshot_time):
            _make_snapshot(secondary_snapshot_time)
        if FLAGS.remove_stale_snapshots_demo_only:
            model.remove_stale_snapshots_for_demo(
                primary_snapshot_time - FLAGS.contest_primary_snapshot_interval * 100)
    except Exception:
        eventlog.exception('cron job failure')
