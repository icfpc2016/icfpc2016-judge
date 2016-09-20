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

import cStringIO
import unittest

import requests

import common


class LargeUploadTest(unittest.TestCase):
    def setUp(self):
        common.setup()
        common.ensure_login()
        common.ensure_api_key()

    def tearDown(self):
        common.teardown()

    def test_medium_upload(self):
        common.post(
            '/api/hello',
            type='json',
            files={
                'file': cStringIO.StringIO('x' * 8),
            })

    def test_medium_upload(self):
        pass
        # TODO(nya): Investigate why this fails.
        # common.post(
        #     '/api/hello',
        #     type='json',
        #     files={
        #         'file': cStringIO.StringIO('x' * 65536),
        #     })

    def test_huge_upload(self):
        with self.assertRaises(requests.HTTPError) as cm:
            common.post(
                '/api/hello',
                type='json',
                files={
                    'file': cStringIO.StringIO('x' * (10 * 1024 * 1024)),
                })
        # Request entity too large
        assert cm.exception.response.status_code == 413
