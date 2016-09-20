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

import requests

import common


class GzipTest(unittest.TestCase):
    def setUp(self):
        common.setup()

    def tearDown(self):
        common.teardown()

    def test_require_gzip(self):
        common.ensure_login()
        common.ensure_api_key()
        with self.assertRaises(requests.HTTPError) as cm:
            common.context.session.headers['Accept-Encoding'] = ''
            common.get('/api/hello', type='json')
        assert cm.exception.response.status_code == 400
        common.context.session.headers['Accept-Encoding'] = 'gzip'
        common.get('/api/hello', type='json')
