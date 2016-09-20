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

import unittest

import common


class CronTest(unittest.TestCase):
    def setUp(self):
        common.setup()

    def tearDown(self):
        common.teardown()

    def test_snapshot_job(self):
        common.ensure_login()
        common.ensure_api_key()
        common.get(
            '/testing/cron/snapshot_job',
            headers={'X-Override-Time': '1451610001'})
        res, data = common.get('/api/snapshot/list', type='json')
        for entry in data['snapshots']:
            if entry['snapshot_time'] == 1451610000:
                break
        else:
            assert False, data
        res, data = common.get('/api/blob/%s' % entry['snapshot_hash'], type='json')
        assert data['snapshot_time'] == 1451610000
        assert not data['problems']
        assert any(
            e['username'] == common.context.username
            for e in data['leaderboard'])
        assert any(
            u['username'] == common.context.username
            for u in data['users'])
