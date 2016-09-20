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

import common


class ExampleTest(unittest.TestCase):
    def setUp(self):
        common.setup()

    def tearDown(self):
        common.teardown()

    def test_submit_problem(self):
        self.assertEqual(42, 6*7)

# Change the above line, and see assertion error something like

# FAIL: test_submit_problem (example_test.ExampleTest)
# ----------------------------------------------------------------------
# Traceback (most recent call last):
#   File "/home/nushio/hub/icfpc2016-misc/hibiki/app/tests/example_test.py", line 12, in test_submit_problem
#     self.assertEqual(54, 6*7)
# AssertionError: 54 != 42
