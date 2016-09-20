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

import datetime
import logging
import signal
import sys
import threading

import apscheduler.schedulers.background
import gflags

from hibiki import cron_jobs
# In order to pull flag definitions.
from hibiki import devserver_main as _devserver_main_import_only
from hibiki import model
from hibiki import settings
from hibiki import setup

FLAGS = gflags.FLAGS


def main():
    setup.setup_common()
    model.connect()

    assert FLAGS.contest_secondary_snapshot_interval >= 10

    shutdown_event = threading.Event()
    def shutdown_handler(signum, frame):
        shutdown_event.set()
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    sched = apscheduler.schedulers.background.BackgroundScheduler()
    sched.add_job(
        cron_jobs.snapshot_job,
        'interval',
        seconds=FLAGS.contest_secondary_snapshot_interval,
        start_date=datetime.datetime.fromtimestamp(
            settings.get_last_secondary_snapshot_time() + 5),
        end_date=datetime.datetime.fromtimestamp(FLAGS.contest_end_time + 6))
    sched.start()

    # We need to set some timeout to allow signal handler interruption.
    while shutdown_event.wait(283) != True:
        pass

    logging.info('Gracefully shutting down the cron process')
    sched.shutdown()
    logging.info('Finished the cron process')


if __name__ == '__main__':
    sys.exit(main())
