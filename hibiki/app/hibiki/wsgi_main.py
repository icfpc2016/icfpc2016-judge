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

import sys

import bottle
import gflags
import wsgiprof

from hibiki import cron_flags as _cron_flags_import_only
from hibiki import handler as _handler_import_only
from hibiki import model
from hibiki import setup

FLAGS = gflags.FLAGS

gflags.DEFINE_bool('profile', False, 'Enable WSGI profiler.')


assert __name__ == 'hibiki.wsgi_main'

app = bottle.default_app()

setup.setup_common()
model.connect()

if FLAGS.profile:
    app = wsgiprof.ProfileMiddleware(app)
