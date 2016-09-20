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

import bs4
import requests
import ujson


class Context(object):
    xsrf_token = None
    api_key = None
    username = None

    def __init__(self):
        self.session = requests.Session()


context = None


def setup():
    global context
    context = Context()


def teardown():
    global context
    context = None


def _request(method, path, type, **kwargs):
    url = 'http://localhost:8000%s' % path
    res = method(url, **kwargs)
    res.raise_for_status()
    if type == 'html':
        assert 'text/html' in res.headers['Content-Type']
        doc = bs4.BeautifulSoup(res.text, 'html5lib')
    elif type == 'text':
        assert 'text/plain' in res.headers['Content-Type']
        doc = res.text
    elif type == 'json':
        assert ('application/json' in res.headers['Content-Type'] or
                'text/plain' in res.headers['Content-Type'])
        doc = ujson.loads(res.text)
    else:
        assert False, type
    return (res, doc)


def get(path, type='html', **kwargs):
    return _request(context.session.get, path, type, **kwargs)


def post(path, type='html', **kwargs):
    kwargs.setdefault('data', {})['xsrf_token'] = context.xsrf_token
    return _request(context.session.post, path, type, **kwargs)


def ensure_login():
    if 'username' in context.session.cookies:
        return

    ensure_xsrf_token()

    res, doc = post(
        '/register',
        data={
            'display_name': 'Team 6',
            'contact_email': 'test@example.com',
            'member_names': 'Akatsuki\nHibiki\nIkazuchi\nInazuma\n',
            'nationalities': '',
            'languages': '',
            'source_url': '',
        })
    username = doc.select('#username')[0].get_text()
    password = doc.select('#password')[0].get_text()
    context.username = username

    res, doc = post(
        '/login',
        data={
            'username': username,
            'password': password,
        })
    assert res.url.endswith('/')
    assert 'username' in context.session.cookies

    ensure_xsrf_token()


def ensure_xsrf_token():
    res, doc = get('/register')
    context.xsrf_token = doc.select('input[name=xsrf_token]')[0]['value']


def ensure_api_key():
    res, doc = get('/apihelp')
    context.api_key = doc.select('#api_key')[0].get_text()
    context.session.headers['X-API-Key'] = context.api_key
