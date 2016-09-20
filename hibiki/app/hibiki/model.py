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

import hashlib
import json
import logging
import os

import bson.binary
import gflags
from passlib.hash import sha256_crypt
import pymongo
import pymongo.collection
import pymongo.errors
import ujson

from hibiki import misc_util
from hibiki import scoring
from hibiki import settings
from hibiki import storage

FLAGS = gflags.FLAGS

gflags.DEFINE_string(
    'mongodb_url', 'mongodb://localhost',
    'MongoDB URL to connect to.')
gflags.DEFINE_string(
    'mongodb_db', 'icfpcontest2016',
    'MongoDB database name.')
gflags.DEFINE_bool(
    'mongodb_explain', False,
    'Log MongoDB query explains.')
gflags.DEFINE_string(
    'storage_gcs_bucket_name', None,
    'Name of the GCS bucket used to storage large blobs.')
gflags.DEFINE_bool(
    'disable_model_cache_for_testing', False,
    'Disables model caching for testing.')

# MongoClient instance.
_client = None

# Collection instance.
_db = None

# The master secret key used to sign cookies.
_cookie_master_secret = None

# Value of password_hash field for passwordless login users.
PASSWORDLESS_HASH = '*passwordless*'


def connect():
    """Connects to the database."""
    global _client
    global _db
    assert not _client, 'connect() called multiple times!'

    _client = pymongo.MongoClient(FLAGS.mongodb_url)
    _db = _client[FLAGS.mongodb_db]

    # Ensure the server version is 2.6+.
    server_version = tuple(_client.server_info()['version'].split('.'))
    assert server_version >= (2, 6), (
        'MongoDB server version is old. Please upgrade to 2.6+.')

    # Connect to GCS if enabled.
    if FLAGS.storage_gcs_bucket_name:
        storage.connect(FLAGS.storage_gcs_bucket_name)

    _init_model()


def _init_model():
    _ensure_cookie_secret()
    _ensure_indices()
    _ensure_organizer_users()


def _ensure_cookie_secret():
    """Makes sure cookie secret is cached."""
    global _cookie_master_secret
    entry = _db.config.find_one({'_id': 'cookie_master_secret'})
    if not entry:
        tmp_cookie_master_secret = misc_util.generate_random_id(length=32)
        try:
            entry = {
                '_id': 'cookie_master_secret',
                'value': tmp_cookie_master_secret,
            }
            _db.config.insert_one(entry)
        except pymongo.errors.DuplicateKeyError:
            entry = _db.config.find_one({'_id': 'cookie_master_secret'})
    assert entry
    _cookie_master_secret = entry['value']


def _ensure_indices():
    """Makes sure indices are built."""
    # For get_all_users()
    _db.users.create_index([
        ('create_time', pymongo.ASCENDING),
    ], background=True)
    # For get_user_by_api_key()
    _db.users.create_index([
        ('api_key', pymongo.ASCENDING),
    ], background=True)
    # For get_public_problems(), count_public_problems(), get_public_problem()
    _db.problems.create_index([
        ('public', pymongo.ASCENDING),
        ('_id', pymongo.ASCENDING),
    ], background=True)
    # For publish_scheduled_problems()
    _db.problems.create_index([
        ('public', pymongo.ASCENDING),
        ('publish_time', pymongo.ASCENDING),
    ], background=True)
    _db.problems.create_index([
        ('publish_time', pymongo.ASCENDING),
    ], background=True)
    # For get_last_problem_ranking_snapshot()
    _db.problem_ranking_snapshots.create_index([
        ('problem_id', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.problem_ranking_snapshots.create_index([
        ('public', pymongo.ASCENDING),
        ('problem_id', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    # For update_problem_rankings()
    _db.problems.create_index([
        ('public', pymongo.ASCENDING),
        ('publish_time', pymongo.ASCENDING),
    ], background=True)
    _db.problem_ranking_snapshots.create_index([
        ('problem_id', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.solutions.create_index([
        ('problem_id', pymongo.ASCENDING),
        ('create_time', pymongo.ASCENDING),
    ], background=True)
    # For get_last_leaderboard_snapshot()
    _db.leaderboard_snapshots.create_index([
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.leaderboard_snapshots.create_index([
        ('public', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    # For update_leaderboard_snapshot()
    _db.problem_ranking_snapshots.create_index([
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.leaderboard_snapshots.create_index([
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    # For get_public_contest_snapshots()
    _db.public_contest_snapshots.create_index([
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    # For update_public_contest_snapshot()
    _db.problem_ranking_snapshots.create_index([
        ('public', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.leaderboard_snapshots.create_index([
        ('public', pymongo.ASCENDING),
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    _db.public_contest_snapshots.create_index([
        ('snapshot_time', pymongo.ASCENDING),
    ], background=True)
    # For get_user_problems()
    _db.problems.create_index([
        ('owner', pymongo.ASCENDING),
    ], background=True)
    # For get_user_solutions()
    _db.solutions.create_index([
        ('owner', pymongo.ASCENDING),
    ], background=True)


def _ensure_organizer_users():
    """Makes sure organizer users are registered."""
    try:
        _db.config.insert_one(
            {
                '_id': 'user_counter',
                'value': 10,
            })
    except pymongo.errors.DuplicateKeyError:
        return
    for i in xrange(10):
        username = '%d' % (i + 1)
        api_key = '%s-%s' % (username, misc_util.generate_random_id(32))
        display_name = 'Contest Organizer Problem Set %s' % chr(ord('A') + i)
        contact_email = 'organizer%d@example.com' % (i + 1)
        member_names = 'N/A'
        remote_host = '127.127.127.%d' % i
        user = {
            '_id': username,
            'password_hash': PASSWORDLESS_HASH,
            'api_key': api_key,
            'display_name': display_name,
            'contact_email': contact_email,
            'member_names': member_names,
            'create_time': misc_util.time(),
            'register_remote_host': remote_host,
            'organizer': True,
        }
        # No other client should be performing conflicting insertions.
        _db.users.insert_one(user)


def _maybe_explain_query(cursor):
    if FLAGS.mongodb_explain:
        logging.info(
            'EXPLAIN: %s',
            json.dumps(
                cursor.explain()['queryPlanner']['winningPlan'], indent=2))


def _increment_atomic_counter(key):
    try:
        entry = _db.config.find_one_and_update(
            {'_id': key},
            {
                '$setOnInsert': {'_id': key},
                '$inc': {'value': 1},
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.AFTER)
    except pymongo.errors.DuplicateKeyError:
        entry = _db.config.find_one_and_update(
            {'_id': key},
            {'$inc': {'value': 1}},
            return_document=pymongo.collection.ReturnDocument.AFTER)
    return entry['value']


def record_last_api_access_time(username):
    """Sets the last API access time.

    Args:
        username: Username.

    Returns:
        The number of seconds since the last access.
    """
    now = misc_util.time()
    try:
        entry = _db.api_last_accesses.find_one_and_update(
            {'_id': username},
            {
                '$setOnInsert': {'_id': username},
                '$set': {'last_access_time': now},
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.BEFORE)
    except pymongo.errors.DuplicateKeyError:
        entry = _db.api_last_accesses.find_one_and_update(
            {'_id': username},
            {'$set': {'last_access_time': now}},
            return_document=pymongo.collection.ReturnDocument.BEFORE)
    if not entry:
        return 86400  # almost forever
    return now - entry['last_access_time']


def increment_api_rate_limit_counter(username, action):
    """Increments API rate limit counter.

    API rate limit is implemented by simply counting requests in a window
    whose length is defined by --api_rate_limit_window_size.

    Args:
        username: Username.
        action: Action name.

    Returns:
        An integer of the rate limit count after increment.
    """
    last_window_time = misc_util.align_timestamp(
        misc_util.time(), FLAGS.contest_start_time, FLAGS.api_rate_limit_window_size)
    key = '%s:%d:%s' % (action, last_window_time, username)
    try:
        entry = _db.api_rate_limits.find_one_and_update(
            {'_id': key},
            {
                '$setOnInsert': {'_id': key},
                '$inc': {'value': 1},
            },
            upsert=True,
            return_document=pymongo.collection.ReturnDocument.AFTER)
    except pymongo.errors.DuplicateKeyError:
        entry = _db.api_rate_limits.find_one_and_update(
            {'_id': key},
            {'$inc': {'value': 1}},
            return_document=pymongo.collection.ReturnDocument.AFTER)
    return entry['value']


def decrement_web_rate_limit_counter(username):
    """Decrements web rate limit counter.

    Web rate limit is implemented by token bucket method.

    Args:
        username: Username.

    Returns:
        True if the request is allowed, otherwise False.
    """
    while True:
        current_time_millis = int(misc_util.time() * 1000)
        # Get the latest entry.
        entry = _db.web_rate_limits.find_one({'_id': username})
        if not entry:
            entry = {
                '_id': username,
                'last_access_time_millis': current_time_millis,
                'tokens': FLAGS.web_rate_limit_allowed_burst_requests,
            }
            try:
                _db.web_rate_limits.insert_one(entry)
            except pymongo.errors.DuplicateKeyError:
                entry = _db.web_rate_limits.find_one({'_id': username})
        last_tokens = entry['tokens']
        last_access_time_millis = entry['last_access_time_millis']
        current_time_millis = int(misc_util.time() * 1000)
        if last_access_time_millis >= current_time_millis:
            # Clock skew? No way to fill tokens, go to the decrement phase.
            break
        # Try filling tokens.
        delta_minutes = (current_time_millis - last_access_time_millis) / 60000.0
        new_tokens = min(
            FLAGS.web_rate_limit_allowed_burst_requests,
            last_tokens + FLAGS.web_rate_limit_requests_per_minute * delta_minutes)
        entry = _db.web_rate_limits.find_one_and_update(
            {
                '_id': username,
                'last_access_time_millis': last_access_time_millis,
            },
            {
                '$set': {
                    'last_access_time_millis': current_time_millis,
                    'tokens': new_tokens,
                },
            },
            return_document=pymongo.collection.ReturnDocument.AFTER)
        if entry:
            break
        # If the update failed, it is a race with other frontends. Try again.
    # Now tokens are filled, try decrement.
    entry = _db.web_rate_limits.find_one_and_update(
        {
            '_id': username,
            'tokens': {'$gte': 1},
        },
        {
            '$inc': {
                'tokens': -1,
            },
        },
        return_document=pymongo.collection.ReturnDocument.AFTER)
    return bool(entry)


def get_cookie_master_secret():
    assert _cookie_master_secret
    if FLAGS.disable_model_cache_for_testing:
        _ensure_cookie_secret()
    return _cookie_master_secret


def perform_health_checks():
    """Performs health checks."""
    _increment_atomic_counter('test')


def save_blob(blob, mimetype):
    """Saves a blob in the large blob storage.

    Args:
        blob: A str.
        mimetype: MIME type.

    Returns:
        A blob key that can be used to lookup the blob later.
    """
    if isinstance(blob, unicode):
        blob = blob.encode('ascii')
    assert isinstance(blob, str)
    key = hashlib.sha1(blob).hexdigest()
    if FLAGS.storage_gcs_bucket_name:
        storage.save('blobs/%s' % key, blob, mimetype=mimetype)
    else:
        try:
            _db.blobs.update_one(
                {'_id': key},
                {'$setOnInsert': {'_id': key, 'value': bson.binary.Binary(blob)}},
                upsert=True)
        except pymongo.errors.DuplicateKeyError:
            pass
    return key


def load_blob(key):
    """Loads a blob from the large blob storage.

    Args:
        key: A blob key.

    Returns:
        str.

    Raises:
        KeyError: Blob entry was not found.
    """
    if FLAGS.storage_gcs_bucket_name:
        return storage.load('blobs/%s' % key)
    else:
        entry = _db.blobs.find_one({'_id': key})
        if not entry:
            raise KeyError('Blob not found: %s' % key)
        return str(entry['value'])


def get_signed_blob_url(key):
    """Returns an external URL serving the blob.

    Args:
        key: A blob key.

    Returns:
        URL string, or None if it is not avaiable.
    """
    if not FLAGS.storage_gcs_bucket_name:
        return None
    return storage.get_signed_url('blobs/%s' % key)


def register_user(display_name, contact_email, member_names, nationalities, languages, source_url, remote_host):
    """Registers a new user.

    Values must be validated in advance.

    Args:
        display_name: Display name.
        contact_email: Contact email address.
        member_names: Member names (multiline text).
        nationalities: Nationalities.
        languages: Languages.
        source_url: URL to the source code.
        remote_host: Remote host of the user.

    Returns:
        (username, password)
    """
    team_id = _increment_atomic_counter('user_counter')
    username = '%d' % team_id
    password = misc_util.generate_password()
    password_hash = sha256_crypt.encrypt(password)
    api_key = '%s-%s' % (username, misc_util.generate_random_id(32))
    user = {
        '_id': username,
        'password_hash': password_hash,
        'api_key': api_key,
        'display_name': display_name,
        'contact_email': contact_email,
        'member_names': member_names,
        'nationalities': nationalities,
        'languages': languages,
        'source_url': source_url,
        'create_time': misc_util.time(),
        'register_remote_host': remote_host,
        'organizer': False,
    }
    _db.users.insert_one(user)
    return (username, password)


def update_user(
        username, display_name=None, contact_email=None, member_names=None,
        nationalities=None, languages=None, source_url=None):
    """Updates a user profile.

    Values must be validated in advance.

    Args:
        username: The username.
        display_name: Display name.
        contact_email: Contact email address.
        member_names: Member names (multiline text).
        nationalities: Nationalities.
        languages: Languages.
        source_url: URL to the source code.
    """
    update = {}
    if display_name is not None:
        update['display_name'] = display_name
    if contact_email is not None:
        update['contact_email'] = contact_email
    if member_names is not None:
        update['member_names'] = member_names
    if nationalities is not None:
        update['nationalities'] = nationalities
    if languages is not None:
        update['languages'] = languages
    if source_url is not None:
        update['source_url'] = source_url
    if update:
        _db.users.update_one({'_id': username}, {'$set': update})


def get_user(username):
    """Returns the specified user.

    Args:
        username: The username.

    Returns:
        A user dictionary.

    Raises:
        KeyError: If the specified user is not found.
    """
    user = _db.users.find_one({'_id': username})
    if not user:
        raise KeyError('User not found: %s' % username)
    return user


def get_user_problems(username):
    """Returns all problems submitted by the specified user.

    Args:
        username: The username.

    Returns:
        A problem list.

    Raises:
        KeyError: If the specified user is not found.
    """
    user = _db.users.find_one({'_id': username})
    if not user:
        raise KeyError('User not found: %s' % username)
    cursor = _db.problems.find(
        {
            'owner': user['_id']
        },
        projection=('owner', 'problem_size', 'solution_size', 'public', '_id'))
    problems = list(cursor)
    enhance_problems_for_admin(problems)
    return problems

def get_user_solutions(username):
    """Returns all solutions submitted by the specified user.

    Args:
        username: The username.

    Returns:
        A solution list.

    Raises:
        KeyError: If the specified user is not found.
    """
    user = _db.users.find_one({'_id': username})
    if not user:
        raise KeyError('User not found: %s' % username)
    solutions = _db.solutions.find(
        {
            'owner': user['_id']
        },
        projection=('resemblance_int', 'solution_size', 'problem_id', '_id'))

    # manually select the best (and oldest) solution
    table = {}
    for solution in solutions:
        problem_id = solution['problem_id']
        if problem_id in table:
            old_solution = table[problem_id]
            if solution['resemblance_int'] > old_solution['resemblance_int'] or \
                (solution['resemblance_int'] == old_solution['resemblance_int'] and solution['_id'] < old_solution['_id']):
                table[problem_id] = solution
        else:
            table[problem_id] = solution

    # sort by problem_id
    solutions = table.values()
    solutions.sort(key=lambda solution: solution['problem_id'])

    return solutions


def get_user_map(usernames):
    """Looks up multiple users at once.

    Args:
        usernames: List of usernames.

    Returns:
        A map from usernames to user dictionaries.
    """
    users = list(_db.users.find({'_id': {'$in': list(set(usernames))}}))
    return {user['_id']: user for user in users}


def get_user_by_api_key(api_key):
    """Looks up a user by an API key.

    Args:
        api_key: API key.

    Returns:
        A user dictionary.

    Raises:
        KeyError: If the specified user is not found.
    """
    if not api_key:
        raise KeyError('User not found by API key')
    user = _db.users.find_one({'api_key': api_key})
    if not user:
        raise KeyError('User not found by API key')
    return user


def get_all_users(**options):
    """Returns all users.

    Args:
        **options: Options passed to query.

    Returns:
        A list of user dictionaries.
    """
    cursor = _db.users.find(
        {},
        sort=[('create_time', pymongo.ASCENDING)],
        **options)
    return list(cursor)


def enqueue_problem(
        owner, problem_spec, problem_size, solution_spec, solution_size,
        create_time, publish_time, processing_time, publish_immediately):
    """Registers a new problem.

    Args:
        owner: Owner username.
        problem_spec: Problem specification string.
        problem_size: Problem size.
        solution_spec: Solution specification string.
        solution_size: Solution size.
        create_time: Timestamp when this problem is submitted.
        publish_time: Timestamp when this problem should be published.
        processing_time: Processing time in seconds.
        publish_immediately: Set to True if this problem should be marked
            public immediately.

    Returns:
        A newly created problem dictionary.
    """
    assert isinstance(publish_time, int)
    problem_spec_hash = save_blob(problem_spec, mimetype='text/plain')
    solution_spec_hash = save_blob(solution_spec, mimetype='text/plain')
    new_problem = {
        '_id': _increment_atomic_counter('problem_counter'),
        'create_time': create_time,
        'owner': owner,
        'problem_spec_hash': problem_spec_hash,
        'problem_size': problem_size,
        'solution_spec_hash': solution_spec_hash,
        'solution_size': solution_size,
        'public': publish_immediately,
        'publish_time': publish_time,
        'processing_time': processing_time,
    }
    _db.problems.insert_one(new_problem)
    return new_problem


def get_public_problems(**options):
    """Returns the list of all public problems present in the database.

    Args:
        **options: Options passed to query.

    Returns:
        A list of problem dictionaries.
    """
    cursor = _db.problems.find(
        {'public': True},
        sort=[('_id', pymongo.ASCENDING)],
        **options)
    return list(cursor)


def count_public_problems():
    """Returns the count of all public problems present in the database.

    Returns:
        Count of all public problems.
    """
    cursor = _db.problems.find(
        {'public': True},
        sort=[('_id', pymongo.DESCENDING)])
    return cursor.count()


def get_public_problem(problem_id):
    """Returns a problem.

    Args:
        problem_id: Numeric ID of the problem.

    Returns:
        A problem dictionary.

    Raises:
        KeyError: If the specified problem was not found, or the problem is
            not yet public.
    """
    problem = _db.problems.find_one({'_id': problem_id, 'public': True})
    if not problem:
        raise KeyError('Problem not found: %s' % problem_id)
    return problem


def count_all_problems_for_admin():
    """Returns the number of all problems.

    Returns:
        The count.
    """
    return _db.problems.find({}).count()


def get_all_problems_for_admin(**options):
    """Returns all problems.

    Args:
        **options: Options passed to query.

    Returns:
        A list of problem dictionaries.
    """
    cursor = _db.problems.find(
        {},
        sort=[('_id', pymongo.ASCENDING)],
        **options)
    problems = list(cursor)
    enhance_problems_for_admin(problems)
    return problems


def get_problem_for_admin(problem_id):
    """Returns a problem.

    Args:
        problem_id: Numeric ID of the problem.

    Returns:
        A problem dictionary.

    Raises:
        KeyError: If the specified problem was not found.
    """
    problem = _db.problems.find_one({'_id': problem_id})
    if not problem:
        raise KeyError('Problem not found: %s' % problem_id)
    return problem


def register_solution(
        owner, problem_id, problem_spec_hash, solution_spec, solution_size,
        resemblance_int, processing_time):
    """Registers a new solution.

    Args:
        owner: Owner username.
        problem_id: Numeric ID of the problem.
        problem_spec_hash: Problem specification hash string.
        solution_spec: Solution specification string.
        solution_size: Solution size.
        resemblance_int: Resemblance value as an integer.
        processing_time: Processing time in seconds.

    Returns:
        A newly created solution dictionary.
    """
    solution_spec_hash = save_blob(solution_spec, mimetype='text/plain')
    new_solution = {
        '_id': _increment_atomic_counter('solution_counter'),
        'create_time': misc_util.time(),
        'owner': owner,
        'problem_id': problem_id,
        'problem_spec_hash': problem_spec_hash,
        'solution_spec_hash': solution_spec_hash,
        'solution_size': solution_size,
        'resemblance_int': resemblance_int,
        'processing_time': processing_time,
    }
    _db.solutions.insert_one(new_solution)
    return new_solution


def count_all_solutions_for_admin():
    """Returns the number of all solutions.

    Returns:
        The count.
    """
    return _db.solutions.find({}).count()


def get_all_solutions_for_admin(**options):
    """Returns all solutions.

    Args:
        **options: Options passed to query.

    Returns:
        A list of solution dictionaries.
    """
    cursor = _db.solutions.find(
        {},
        sort=[('_id', pymongo.ASCENDING)],
        **options)
    return list(cursor)


def get_solution_for_admin(solution_id):
    """Returns a solution.

    Args:
        solution_id: Numeric ID of the solution.

    Returns:
        A solution dictionary.

    Raises:
        KeyError: If the specified solution was not found, or the solution is
            not visible to the user.
    """
    solution = _db.solutions.find_one({'_id': solution_id})
    if not solution:
        raise KeyError('Solution not found: %s' % solution_id)
    return solution


def publish_scheduled_problems():
    """Publishes scheduled problems."""
    last_published_problem = _db.problems.find_one(
        {'public': True},
        sort=[('publish_time', pymongo.DESCENDING)])
    last_publish_time = (
        last_published_problem['publish_time'] if last_published_problem
        else 0)
    cursor = _db.problems.find(
        {
            'publish_time': {'$lte': misc_util.time(), '$gt': last_publish_time},
        },
        sort=[('_id', pymongo.DESCENDING)],
        projection=('owner', 'publish_time', '_id', 'public'))
    publishing_problem_ids = []
    publishing_pairs = set()
    for problem in cursor:
        if problem['public']:
            break
        pair = (problem['owner'], problem['publish_time'])
        if pair not in publishing_pairs:
            publishing_pairs.add(pair)
            publishing_problem_ids.append(problem['_id'])
    if publishing_problem_ids:
        _db.problems.update_many(
            {'_id': {'$in': publishing_problem_ids}},
            {'$set': {'public': True}})


def get_last_problem_ranking_snapshot(problem_id, public_only):
    """Returns the last problem ranking snapshot.

    Args:
        problem_id: Numeric ID of the problem.
        public_only: If true, only public snapshots are considered.

    Returns:
        (snapshot_time, ranking)
        ranking = [
           {'owner': ..., 'resemblance_int': ..., 'solution_size': ...},
           ...
        ]
    """
    query = {
        'problem_id': problem_id,
        'snapshot_time': {'$lte': misc_util.time()},
    }
    if public_only:
        query['public'] = True
    snapshot = _db.problem_ranking_snapshots.find_one(
        query,
        sort=[('snapshot_time', pymongo.DESCENDING)])
    if not snapshot:
        return (FLAGS.contest_start_time, [])
    return (snapshot['snapshot_time'], snapshot['ranking'])


def _update_problem_ranking_snapshot(snapshot_time, problem_id):
    assert settings.is_secondary_snapshot_time(snapshot_time)
    last_snapshot = _db.problem_ranking_snapshots.find_one(
        {
            'problem_id': problem_id,
            'snapshot_time': {'$lte': snapshot_time},
        },
        sort=[('snapshot_time', pymongo.DESCENDING)])
    if not last_snapshot:
        problem = _db.problems.find_one({'_id': problem_id})
        last_snapshot = {
            'problem_id': None,
            'snapshot_time': 0,
            'problem': problem,
            'ranking': [],
        }
    if last_snapshot['snapshot_time'] == snapshot_time:
        return
    owner_to_entry = {
        entry['owner']: entry
        for entry in last_snapshot['ranking']
    }
    cursor = _db.solutions.find(
        {
            'problem_id': problem_id,
            'create_time': {
                '$lt': snapshot_time,
                '$gte': last_snapshot['snapshot_time'],
            },
        },
        projection=('_id', 'owner', 'resemblance_int', 'solution_size'))
    for solution in cursor:
        last_entry = owner_to_entry.get(
            solution['owner'], {'resemblance_int': -1})
        if (solution['resemblance_int'] > last_entry['resemblance_int'] or
                (solution['resemblance_int'] == last_entry['resemblance_int'] and
                 solution['solution_size'] < last_entry['solution_size'])):
            owner_to_entry[solution['owner']] = {
                'owner': solution['owner'],
                'solution_id': solution['_id'],
                'resemblance_int': solution['resemblance_int'],
                'solution_size': solution['solution_size'],
            }
    ranking = owner_to_entry.values()
    ranking.sort(key=lambda entry: (
        -entry['resemblance_int'], entry['solution_size'], entry['solution_id']))
    key = '%d:%d' % (problem_id, snapshot_time)
    public = settings.is_public_problem_ranking_snapshot_time(snapshot_time)
    try:
        _db.problem_ranking_snapshots.update_one(
            {'_id': key},
            {
                '$setOnInsert': {'_id': key},
                '$set': {
                    'problem_id': problem_id,
                    'snapshot_time': snapshot_time,
                    'problem': last_snapshot['problem'],
                    'ranking': ranking,
                    'public': public,
                },
            },
            upsert=True)
    except pymongo.errors.DuplicateKeyError:
        pass


def update_problem_ranking_snapshots(snapshot_time):
    """Updates problem rankings.

    Args:
        snapshot_time: Timestamp of the snapshot.
    """
    assert settings.is_secondary_snapshot_time(snapshot_time)
    cursor = _db.problems.find(
        {
            'public': True,
            'publish_time': {'$lte': snapshot_time},
        },
        projection=['_id'])
    problem_ids = [problem['_id'] for problem in cursor]
    for problem_id in problem_ids:
        _update_problem_ranking_snapshot(snapshot_time, problem_id)


def get_last_leaderboard_snapshot(public_only):
    """Returns the last leaderboard snapshot.

    Args:
        public_only: If true, only public snapshots are considered.

    Returns:
        (snapshot_time, ranking)
        ranking = [
           {'username': ..., 'score': ...},
           ...
        ]
    """
    query = {
        'snapshot_time': {
            '$lte': misc_util.time(),
        },
    }
    if public_only:
        query['public'] = True
    snapshot = _db.leaderboard_snapshots.find_one(
        query,
        sort=[('snapshot_time', pymongo.DESCENDING)])
    if not snapshot:
        return (FLAGS.contest_start_time, [])
    return (snapshot['snapshot_time'], snapshot['ranking'])


def update_leaderboard_snapshot(snapshot_time):
    """Updates leaderboard.

    This function must be called after update_problem_rankings() with the same
    |snapshot_time|.

    Args:
        snapshot_time: Timestamp of the snapshot.
    """
    assert settings.is_secondary_snapshot_time(snapshot_time)
    cursor = _db.problem_ranking_snapshots.find({'snapshot_time': snapshot_time})
    all_users = get_all_users()
    team_scores = {
        user['_id']: 0.0
        for user in all_users
    }
    organizers = [user['_id'] for user in all_users if user['organizer']]
    for snapshot in cursor:
        # Do not include scores for problems published at the snapshot time.
        if snapshot['problem']['publish_time'] == snapshot_time:
            continue
        for username, score in scoring.compute_team_scores_for_problem(
                snapshot['problem'], snapshot['ranking']).iteritems():
            team_scores[username] += score
    for username in organizers:
        del team_scores[username]
    ranking = [
        {
            'username': username,
            'score': score,
        }
        for username, score in team_scores.iteritems()
    ]
    ranking.sort(key=lambda entry: (-entry['score'], entry['username']))
    public = settings.is_public_leaderboard_snapshot_time(snapshot_time)
    try:
        _db.leaderboard_snapshots.update_one(
            {'_id': snapshot_time},
            {
                '$setOnInsert': {
                    '_id': snapshot_time,
                },
                '$set': {
                    'snapshot_time': snapshot_time,
                    'ranking': ranking,
                    'public': public,
                },
            },
            upsert=True)
    except pymongo.errors.DuplicateKeyError:
        pass


def get_public_contest_snapshots():
    """Returns the public contest snapshots.

    Returns:
        A list of public contest snapshots.
    """
    cursor = _db.public_contest_snapshots.find(
        {},
        sort=[('snapshot_time', pymongo.ASCENDING)])
    return list(cursor)


def update_public_contest_snapshot(snapshot_time):
    """Updates the contest snapshot.

    This function must be called after update_problem_rankings() and
    update_leaderboard_snapshot() with the same |snapshot_time|.

    Args:
        snapshot_time: Timestamp of the snapshot.
    """
    assert settings.is_primary_snapshot_time(snapshot_time)
    def _compute_contest_snapshot():
        leaderboard_snapshot = _db.leaderboard_snapshots.find_one(
            {
                'public': True,
                'snapshot_time': {'$lte': snapshot_time},
            },
            sort=[('snapshot_time', pymongo.DESCENDING)])
        leaderboard = leaderboard_snapshot['ranking']
        users_map = get_user_map(entry['username'] for entry in leaderboard)
        users = [
            {
                'username': user['_id'],
                'display_name': user['display_name'],
            }
            for user in users_map.values()
        ]
        problems = []
        cursor = _db.problem_ranking_snapshots.find(
            {
                'public': True,
                'snapshot_time': snapshot_time,
            })
        for snapshot in cursor:
            problem = {
                'problem_id': snapshot['problem']['_id'],
                'publish_time': snapshot['problem']['publish_time'],
                'owner': snapshot['problem']['owner'],
                'problem_size': snapshot['problem']['problem_size'],
                'problem_spec_hash': snapshot['problem']['problem_spec_hash'],
                'solution_size': snapshot['problem']['solution_size'],
                'ranking': [
                    {
                        'resemblance': solution['resemblance_int'] / 1000000.0,
                        'solution_size': solution['solution_size'],
                    }
                    for solution in snapshot['ranking']
                ],
            }
            problems.append(problem)
        contest_snapshot = {
            'snapshot_time': snapshot_time,
            'users': users,
            'problems': problems,
            'leaderboard': leaderboard,
        }
        return contest_snapshot

    # Do actual computation in a local function to release memory of
    # intermediate objects.
    contest_snapshot_json = ujson.dumps(
        _compute_contest_snapshot(), double_precision=6)
    contest_snapshot_hash = save_blob(
        contest_snapshot_json, mimetype='application/json')

    try:
        _db.public_contest_snapshots.update_one(
            {'_id': snapshot_time},
            {
                '$setOnInsert': {'_id': snapshot_time},
                '$set': {
                    'snapshot_time': snapshot_time,
                    'snapshot_hash': contest_snapshot_hash,
                },
            },
            upsert=True)
    except pymongo.errors.DuplicateKeyError:
        pass


def remove_stale_snapshots_for_demo(stale_time):
    """Removes stale snapshots.

    This should be used in demo instances only.

    Args:
        stale_time: Timestamp. Snapshots with older than this timestamp
            will be removed.
    """
    _db.problem_ranking_snapshots.delete_many(
        {
            'snapshot_time': {'$lt': stale_time},
        })
    _db.leaderboard_snapshots.delete_many(
        {
            'snapshot_time': {'$lt': stale_time},
        })
    _db.public_contest_snapshots.delete_many(
        {
            'snapshot_time': {'$lt': stale_time},
        })


def lock_snapshot_cron_job(snapshot_time):
    """Obtains a lock for a snapshot cron job.

    Args:
        snapshot_time: Timestamp of the snapshot.

    Returns:
        True if a lock is acquired. Otherwise False.
    """
    try:
        _db.cron_locks.insert_one({
            '_id': 'snapshot:%d' % snapshot_time,
            'locked_time': misc_util.time(),
        })
    except pymongo.errors.DuplicateKeyError:
        return False
    return True


def enhance_problems_for_admin(problems):
    for problem in problems:
        query = {
            'problem_id': problem['_id']
        }
        snapshot = _db.problem_ranking_snapshots.find_one(
            query,
            sort=[('snapshot_time', pymongo.DESCENDING)])
        if snapshot is None:
            problem["solution_count"] = 0
            problem["perfect_solution_count"] = 0
        else:
            problem["solution_count"] = len(snapshot["ranking"])
            perfect_solution_count = 0
            for solution in snapshot["ranking"]:
                if solution["resemblance_int"] == 1000000:
                    perfect_solution_count += 1
            problem["perfect_solution_count"] = perfect_solution_count
