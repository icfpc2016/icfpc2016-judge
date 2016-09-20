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

import os
import unittest

import requests

import common


class SubmitTest(unittest.TestCase):
    def setUp(self):
        common.setup()
        with open(os.path.join(os.path.dirname(__file__), 'sample_solution.txt')) as f:
            self._sample_solution = f.read()

    def tearDown(self):
        common.teardown()

    def submit_problem_web(self, publish_time, current_time):
        common.post(
            '/problem/submit',
            data={
                'solution_spec': self._sample_solution,
                'publish_time': publish_time,
            },
            headers={
                'X-Override-Time': '%d' % current_time,
            })

    def submit_problem_api(self, publish_time, current_time):
        res, data = common.post(
            '/api/problem/submit',
            type='json',
            data={
                'solution_spec': self._sample_solution,
                'publish_time': publish_time,
            },
            headers={
                'X-Override-Time': '%d' % current_time,
            })
        assert data['ok']

    def test_submit_problem_web(self):
        common.ensure_login()
        common.ensure_api_key()
        # publish_time is before the first publish time
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_web(1475279990, 1451606400)
        assert cm.exception.response.status_code == 403
        # Correct publish_time
        self.submit_problem_web(1475280000, 1451606400)
        self.submit_problem_web(1480550400, 1451606400)
        # publish_time is after the last publish time
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_web(1480550410, 1451606400)
        assert cm.exception.response.status_code == 403
        # publish_time is past
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_web(1475280000, 1475280001)
        assert cm.exception.response.status_code == 403

    def test_submit_problem_api(self):
        common.ensure_login()
        common.ensure_api_key()
        # publish_time is before the first publish time
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_api(1475279990, 1451606400)
        assert cm.exception.response.status_code == 403
        # Correct publish_time
        self.submit_problem_api(1475280000, 1451606400)
        self.submit_problem_api(1480550400, 1451606400)
        # publish_time is after the last publish time
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_api(1480550410, 1451606400)
        assert cm.exception.response.status_code == 403
        # publish_time is past
        with self.assertRaises(requests.HTTPError) as cm:
            self.submit_problem_api(1475280000, 1475280001)
        assert cm.exception.response.status_code == 403
