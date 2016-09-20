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

import binascii
import copy
import functools
import logging
import os

import bottle
import gflags
import ujson

from hibiki import misc_util
from hibiki import model
from hibiki import settings

FLAGS = gflags.FLAGS

gflags.DEFINE_bool(
    'admin_only', False,
    'Protect the whole website with basic authentication. Use this flag in '
    'canary instances and pre-launch production instances.')

# Cookie names.
_USERNAME_COOKIE = 'username'
_XSRF_TOKEN_COOKIE = 'xsrf_token'

# bottle.BaseRequest.environ keys.
_USER_DICT_ENVIRON = 'hibiki.user_dict'


def get_current_user():
    """Returns the current user.

    Even if the username is set in the cookie, if the user does not exist in
    backends, this function returns None.

    Returns:
        A user dictionary, or None if the user is not logged in.
    """
    def get_current_user_no_cache():
        username = bottle.request.get_cookie(
            _USERNAME_COOKIE, secret=model.get_cookie_master_secret())
        if not username:
            return None
        try:
            return model.get_user(username)
        except KeyError:
            return None
    # Cache the result in thread local storage (LocalRequest.environ).
    if _USER_DICT_ENVIRON not in bottle.request.environ:
        bottle.request.environ[_USER_DICT_ENVIRON] = get_current_user_no_cache()
    cached_user = bottle.request.environ[_USER_DICT_ENVIRON]
    return copy.deepcopy(cached_user)


def get_current_username():
    """Returns the current user name.

    Even if the username is set in the cookie, if the user does not exist in
    backends, this function returns None.

    Returns:
        Username string, or None if the user is not logged in.
    """
    user = get_current_user()
    if not user:
        return None
    return user['_id']


def set_current_username(username):
    """Sets the current username.

    Args:
        username: The username. If it is None, the user is logged out.
    """
    current_user = get_current_user()
    assert not current_user or not current_user.get('_overridden')
    if not username:
        bottle.response.delete_cookie(_USERNAME_COOKIE)
    else:
        bottle.response.set_cookie(
            _USERNAME_COOKIE, username, secret=model.get_cookie_master_secret())
    # Invalidate the cache.
    bottle.request.environ.pop(_USER_DICT_ENVIRON, None)


def _override_current_user_for_api_request(user):
    """Overrides the current user for API request.

    Args:
        user: User dictionary.
    """
    current_user = get_current_user()
    assert not current_user or not current_user.get('_overridden')
    user = copy.deepcopy(user)
    user['_overridden'] = True
    bottle.request.environ[_USER_DICT_ENVIRON] = user


def _get_session_cookie_secret():
    username = get_current_username()
    if not username:
        return model.get_cookie_master_secret()
    return '%s:%s' % (model.get_cookie_master_secret(), username)


def get_xsrf_token():
    """Returns the XSRF token for the current client.

    Returns:
        XSRF token string, or None if XSRF token is not assigned to the client
        yet.
    """
    return bottle.request.get_cookie(
        _XSRF_TOKEN_COOKIE, secret=_get_session_cookie_secret())


def ensure_xsrf_token():
    """Ensures a XSRF token is assigned to the current client.

    Returns:
        XSRF token string.
    """
    xsrf_token = get_xsrf_token()
    if not xsrf_token:
        xsrf_token = misc_util.generate_random_id(16)
        bottle.response.set_cookie(
            _XSRF_TOKEN_COOKIE, xsrf_token, secret=_get_session_cookie_secret())
    return xsrf_token


def is_admin():
    """Checks if the client is an admin.

    Returns:
        True if the client is an admin.
    """
    return bottle.request.auth == settings.get_admin_credential()


def ensure_admin():
    """Ensures the client is an admin.

    Raises:
        HTTPError: If the client is not authenticated as an admin.
    """
    if not is_admin():
        response = bottle.HTTPError(401, 'Unauthorized')
        response.headers['WWW-Authenticate'] =  'Basic realm="admin only" domain="/"'
        raise response


def _api_auth_hook():
    """Before-request hook to authenticate API requests."""
    if not bottle.request.path.startswith('/api/'):
        return
    api_key = bottle.request.headers.get('X-API-Key', 'N/A')
    try:
        user = model.get_user_by_api_key(api_key)
    except KeyError:
        bottle.abort(403, 'Invalid API key.')
    _override_current_user_for_api_request(user)


def _default_headers_hook():
    """Before-request hook to set default response headers."""
    bottle.response.headers['Cache-Control'] = 'no-store'
    bottle.response.headers['Server'] = 'Hibiki/2016'
    bottle.response.headers['X-Username'] = get_current_username() or ''


def _protect_admin_area_hook():
    """Before-request hook to protect the admin area with authentication."""
    if bottle.request.path.startswith(('/health', '/ping', '/api/')):
        return
    if FLAGS.admin_only or bottle.request.path.startswith('/admin/'):
        ensure_admin()


def _protect_before_contest_hook():
    """Before-request hook to protect the whole website before the contest."""
    if bottle.request.path.startswith(('/health', '/ping', '/api/', '/admin/')):
        return
    if not is_admin() and not settings.has_contest_started():
        bottle.abort(403, 'The contest has not started yet.')


def _enforce_web_rate_limit_hook():
    """Before-request hook to enforce web rate limit."""
    if (FLAGS.enable_load_test_hacks and
            bottle.request.headers.get('X-Load-Test', '') == 'yes'):
        return
    if bottle.request.path.startswith(('/health', '/ping', '/static/', '/api/', '/admin/')):
        return
    user = get_current_user()
    if not user:
        return
    if user['organizer']:
        return
    if not model.decrement_web_rate_limit_counter(user['_id']):
        bottle.abort(429, 'Rate limit exceeded.')


def _protect_xsrf_hook():
    """Before-request hook to protect from XSRF attacks."""
    # No need to protect API calls.
    if bottle.request.path.startswith('/api/'):
        return
    if bottle.request.method not in ('GET', 'HEAD'):
        xsrf_token = bottle.request.forms.get('xsrf_token', 'N/A')
        if xsrf_token != get_xsrf_token():
            bottle.abort(400, 'XSRF token is incorrect or not set.')


def _require_gzip_hook():
    """Before-request hook to require gzip for API requests."""
    if (FLAGS.enable_load_test_hacks and
            bottle.request.headers.get('X-Load-Test', '') == 'yes'):
        return
    if bottle.request.path.startswith('/api/'):
        accept_encoding = bottle.request.headers.get(
            'X-Accept-Encoding',
            bottle.request.headers.get('Accept-Encoding', ''))
        if 'gzip' not in accept_encoding:
            bottle.abort(
                400, 'Accept-Encoding: gzip is required for API requests')


def install_request_hooks():
    """Installs request hooks."""
    bottle.default_app().add_hook('before_request', _api_auth_hook)
    bottle.default_app().add_hook('before_request', _default_headers_hook)
    bottle.default_app().add_hook('before_request', _protect_admin_area_hook)
    bottle.default_app().add_hook('before_request', _protect_before_contest_hook)
    bottle.default_app().add_hook('before_request', _enforce_web_rate_limit_hook)
    bottle.default_app().add_hook('before_request', _protect_xsrf_hook)
    bottle.default_app().add_hook('before_request', _require_gzip_hook)


def require_admin(handler):
    """Bottle handler decorator to require admin.

    Args:
        handler: A Bottle handler function.

    Returns:
        A wrapped Bottle handler function.
    """
    @functools.wraps(handler)
    def wrapped_handler(*args, **kwargs):
        ensure_admin()
        return handler(*args, **kwargs)
    return wrapped_handler


def require_guest(handler):
    """Bottle handler decorator to require the user to be logged out.

    Args:
        handler: A Bottle handler function.

    Returns:
        A wrapped Bottle handler function.
    """
    @functools.wraps(handler)
    def wrapped_handler(*args, **kwargs):
        if get_current_username():
            bottle.redirect('/')
        return handler(*args, **kwargs)
    return wrapped_handler


def require_login(handler):
    """Bottle handler decorator to require the user to be logged in.

    Args:
        handler: A Bottle handler function.

    Returns:
        A wrapped Bottle handler function.
    """
    @functools.wraps(handler)
    def wrapped_handler(*args, **kwargs):
        if not get_current_username():
            bottle.redirect('/')
        return handler(*args, **kwargs)
    return wrapped_handler


def json_api_handler(handler):
    """Bottle handler decorator for JSON REST API handlers.

    Args:
        handler: A Bottle handler function.

    Returns:
        A wrapped Bottle handler function.
    """
    @functools.wraps(handler)
    def wrapped_handler(*args, **kwargs):
        try:
            handler_result = handler(*args, **kwargs)
        except bottle.HTTPResponse as handler_result:
            pass
        except Exception:
            logging.exception('Uncaught exception')
            handler_result = bottle.HTTPError(500, 'Internal Server Error')
        if isinstance(handler_result, bottle.HTTPResponse):
            # For now, we do not support raising successful HTTPResponse.
            assert handler_result.status_code // 100 != 2
            # Forcibly convert HTTPError to HTTPResponse to avoid formatting.
            response = handler_result.copy(cls=bottle.HTTPResponse)
            response_data = {'ok': False, 'error': handler_result.body}
        else:
            assert isinstance(handler_result, dict)
            response = bottle.response.copy(cls=bottle.HTTPResponse)
            response_data = handler_result
            response_data['ok'] = True
        response.body = ujson.dumps(response_data, double_precision=6)
        response.content_type = 'application/json'
        return response
    return wrapped_handler


def render(template_name, template_dict):
    """Renders a HTML template.

    Args:
        template_name: The filename of the template.
        template_dict: A dictionary filled into the template.

    Returns:
        A rendered HTML string.
    """
    real_template_dict = {
        'xsrf_token': ensure_xsrf_token(),
        'current_username': get_current_username(),
        'current_user': get_current_user(),
        'is_admin': is_admin(),
        'format_timestamp': misc_util.format_timestamp,
        'request_path': bottle.request.path,
    }
    real_template_dict.update(template_dict)
    return bottle.jinja2_template(
        template_name, real_template_dict,
        template_settings={'autoescape': True})


def get_form_string(key, max_length, allow_empty=False):
    """Returns a form string after validating the value.

    Args:
        key: Form value key.
        allow_empty: If True, allow an empty string.
        max_length: Maxmimum length of the string.

    Returns:
        A unicode string.

    Raises:
        ValueError: On validation failure.
    """
    raw_value = bottle.request.forms.get(key)
    if raw_value is None:
        raise ValueError('Invalid request: %s not found' % key)
    value = raw_value.decode('utf-8')  # May raise UnicodeDecodeError
    if not allow_empty and not value:
        raise ValueError('Invalid request: %s empty' % key)
    if len(value) > max_length:
        raise ValueError('Invalid request: %s too long' % key)
    return value


def parse_basic_profile_forms():
    """Parses and validates basic profile forms in the request.

    Returns:
        A dictionary containing user profile.

    Raises:
        ValueError: When validation failed.
    """
    return {
        'display_name': get_form_string('display_name', 32),
        'contact_email': get_form_string('contact_email', 256),
        'member_names': get_form_string('member_names', 4096),
        'nationalities': get_form_string('nationalities', 1024, allow_empty=True),
        'languages': get_form_string('languages', 1024, allow_empty=True),
        'source_url': get_form_string('source_url', 2083, allow_empty=True),
    }


def compute_team_display_name_map(usernames):
    """Computes team display_name map.

    Args:
        username: List of usernames.

    Returns:
        A dictionary mapping usernames to display names.
    """
    usernames = list(set(usernames))
    user_map = model.get_user_map(usernames)
    team_display_name_map = {
        username: user_map.get(username, {}).get('display_name', '???')
        for username in usernames
    }
    return team_display_name_map


def inject_ranks_to_ranked_solutions(ranked_solutions):
    """Inject |injected_rank| to ranked solutions.

    Args:
        ranked_solutions: List of solution dictionaries sorted by rank.
    """
    current_rank = 1
    tie_index = -1
    num_ties = 0
    for index, solution in enumerate(ranked_solutions):
        if (tie_index >= 0 and
                solution['resemblance_int'] ==
                ranked_solutions[tie_index]['resemblance_int']):
            num_ties += 1
        else:
            current_rank += num_ties
            tie_index = index
            num_ties = 1
        solution['injected_rank'] = current_rank


def get_post_param(key, default_value=None):
    """Retrieves the parameter either from forms or files.

    Args:
        key: POST parameter key.
        default_value: Default value returned when the parameter is not found
            in the request. If unset or None is specified and the parameter
            is not found, KeyError is raised.

    Returns:
        The value corresponding to |key| in str.

    Raises:
        KeyError: When default_value is None and the key is not found.
    """
    if key in bottle.request.forms:
        return bottle.request.forms[key]
    if key in bottle.request.files:
        return bottle.request.files[key].file.read()
    if not (default_value is None):
        return default_value
    raise KeyError(key)


def enforce_api_rate_limit(action, limit_in_window):
    """Enforces API rate limit.

    Args:
        action: Action name.
        limit_in_window: Maximum number of requests of this action in a window.

    Raises:
        bottle.HTTPError: If the rate limit is exceeded.
    """
    if (FLAGS.enable_load_test_hacks and
            bottle.request.headers.get('X-Load-Test', '') == 'yes'):
        return
    if get_current_user()['organizer']:
        return
    username = get_current_username()
    if (model.record_last_api_access_time(username) <
            FLAGS.api_rate_limit_request_interval):
        bottle.abort(429, 'Rate limit exceeded (per-second limit).')
    count = model.increment_api_rate_limit_counter(username, action)
    if count > limit_in_window:
        bottle.abort(429, 'Rate limit exceeded (per-hour limit).')


# http://flask.pocoo.org/snippets/44/
class Pagination(object):
    def __init__(self, current_page, items_per_page, total_items):
        self.current_page = current_page
        self.items_per_page = items_per_page
        self.total_items = total_items
        self.last_page = (
            (self.total_items + self.items_per_page - 1) / self.items_per_page)
        self.has_prev = self.current_page > 1
        self.has_next = self.current_page < self.last_page

    def iter_pages(self):
        last_printed_page = 0
        for page in xrange(1, self.last_page + 1):
            if (page <= 2 or
                    (self.current_page - 2 <= page <= self.current_page + 5) or
                    self.last_page - 1 <= page):
                if page != last_printed_page + 1:
                    yield None  # ellapsis
                yield page
                last_printed_page = page
