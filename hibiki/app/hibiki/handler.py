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

import json
import logging
import os
import re
import socket

import bottle
import gflags
from passlib.hash import sha256_crypt

from hibiki import cron_jobs
from hibiki import eventlog
from hibiki import game
from hibiki import handler_util
from hibiki import misc_util
from hibiki import model
from hibiki import settings
from hibiki import visualize

FLAGS = gflags.FLAGS

gflags.DEFINE_integer(
    'pagination_items_per_page', 50,
    'The number of pagination items per page.')
gflags.DEFINE_bool(
    'enable_testing_handlers', False,
    'Enables web handlers for testing.')
gflags.DEFINE_string(
    'health_file', None,
    'Marker file used for health reporting')

handler_util.install_request_hooks()


def sushify_char(str):
    if re.match('\d',str):
        ret = "d"+str+".png"
    elif str==".":
        ret = "do.png"
    else:
        i = ord((str+"?")[0])
        ret = "d"+(i%10)+".png"
    return "<img src='/static/sushi/{}'/>".format(ret)

def sushify(sushify_mode, str):
    if sushify_mode:
        return "".join([sushify_char(c) for c in str])
    else:
        return bottle.template('{{str}}', str=str)

def get_sushify_mode():
    t = misc_util.time()
    sushify_mode =  1470571200 < t and t < 1470592800
    if ('sushi_nothanks' in bottle.request.query) : sushify_mode = False
    if ('sushi_please' in bottle.request.query) : sushify_mode = True
    return sushify_mode




@bottle.error(code=500)
def ise_handler(e):
    eventlog.emit(
        'exception',
        {
            'message': 'Internal Server Error',
            'traceback': e.traceback,
        })
    return bottle.default_app().default_error_handler(e)


@bottle.get('/health')
def health_handler():
    bottle.response.content_type = 'text/plain'
    if FLAGS.health_file:
        if not os.path.exists(FLAGS.health_file):
            bottle.response.status = 403
            return 'FAIL'
    try:
        model.perform_health_checks()
    except Exception:
        bottle.response.status = 403
        return 'FAIL'
    return 'ok'


@bottle.get('/ping')
def ping_handler():
    bottle.response.content_type = 'text/plain'
    return socket.gethostname()


@bottle.get('/static/<path:path>')
def static_handler(path):
    return bottle.static_file(
        path,
        root=os.path.join(os.path.dirname(__file__), '..', 'static'))


@bottle.get('/')
def index_handler():
    if 'admin' in bottle.request.query:
        handler_util.ensure_admin()
    if not handler_util.get_current_username():
        return handler_util.render('index_guest.html', {})
    return handler_util.render('index_login.html', {})


@bottle.get('/play')
def play_handler():
    return handler_util.render('play.html', {})


@bottle.get('/register')
@handler_util.require_guest
def register_handler():
    if settings.has_contest_finished():
        bottle.abort(403, 'The contest is over!')
    empty_user = {
        'display_name': '',
        'contact_email': '',
        'member_names': '',
        'nationalities': '',
        'languages': '',
        'source_url': '',
    }
    return handler_util.render('register.html', {'user': empty_user})


@bottle.post('/register')
@handler_util.require_guest
def register_post_handler():
    if settings.has_contest_finished():
        bottle.abort(403, 'The contest is over!')
    try:
        basic_profile = handler_util.parse_basic_profile_forms()
    except ValueError:
        bottle.abort(400, 'Invalid form.')
    username, password = model.register_user(
        remote_host=bottle.request.remote_addr,
        **basic_profile)
    template_dict = {
        'username': username,
        'password': password,
    }
    return handler_util.render('registered.html', template_dict)


@bottle.get('/login')
@handler_util.require_guest
def login_handler():
    msg = bottle.request.query.get('msg', '')
    return handler_util.render('login.html', {'msg': msg})


@bottle.post('/login')
@handler_util.require_guest
def login_post_handler():
    try:
        username = bottle.request.forms['username']
        password = bottle.request.forms['password']
    except KeyError:
        bottle.abort(400, 'Invalid form.')
    try:
        user = model.get_user(username)
    except KeyError:
        bottle.redirect('/login?msg=fail')
    if user['password_hash'] == model.PASSWORDLESS_HASH:
        if not handler_util.is_admin():
            bottle.redirect('/login?msg=fail')
    else:
        if not sha256_crypt.verify(password, user['password_hash']):
            bottle.redirect('/login?msg=fail')
    handler_util.set_current_username(username)
    bottle.redirect('/')


@bottle.post('/logout')
def logout_post_handler():
    handler_util.set_current_username(None)
    bottle.redirect('/')


@bottle.get('/profile')
@handler_util.require_login
def profile_handler():
    user = handler_util.get_current_user()
    msg = bottle.request.query.get('msg', '')
    return handler_util.render('profile.html', {'user': user, 'msg': msg})


@bottle.post('/profile')
@handler_util.require_login
def profile_post_handler():
    try:
        basic_profile = handler_util.parse_basic_profile_forms()
    except ValueError:
        bottle.abort(400, 'Invalid form.')
    username = handler_util.get_current_username()
    model.update_user(username, **basic_profile)
    bottle.redirect('/profile?msg=updated')


@bottle.get('/problem/list')
@handler_util.require_login
def problem_list_handler():
    try:
        page = int(bottle.request.query.get('page', 1))
    except ValueError:
        page = 1
    count = model.count_public_problems()
    problems = model.get_public_problems(
        limit=FLAGS.pagination_items_per_page,
        skip=(page - 1) * FLAGS.pagination_items_per_page)
    team_display_name_map = handler_util.compute_team_display_name_map(
        problem['owner'] for problem in problems)
    pagination = handler_util.Pagination(
        page, FLAGS.pagination_items_per_page, count)
    template_dict = {
        'problems': problems,
        'team_display_name_map': team_display_name_map,
        'pagination': pagination,
    }
    return handler_util.render('problem_list.html', template_dict)


@bottle.get('/problem/view/<problem_id>')
@handler_util.require_login
def problem_view_handler(problem_id):
    try:
        problem_id = int(problem_id)
    except ValueError:
        bottle.abort(404, 'Problem not found.')
    try:
        problem = model.get_public_problem(problem_id=problem_id)
    except KeyError:
        bottle.abort(404, 'Problem not found.')
    owner = model.get_user(problem['owner'])
    problem_spec = model.load_blob(problem['problem_spec_hash'])
    snapshot_time, ranked_solutions = model.get_last_problem_ranking_snapshot(
        problem_id=problem_id, public_only=True)
    handler_util.inject_ranks_to_ranked_solutions(ranked_solutions)
    template_dict = {
        'problem': problem,
        'problem_spec': problem_spec,
        'owner': owner,
        'ranked_solutions': ranked_solutions,
        'snapshot_time': snapshot_time,
    }
    return handler_util.render('problem_view.html', template_dict)


@bottle.get('/problem/submit')
@handler_util.require_login
def problem_submit_handler():
    if handler_util.get_current_user()['organizer']:
        bottle.abort(400, 'You are organizer, use API to submit problems.')
    try:
        next_publish_time = settings.get_next_publish_time()
    except ValueError:
        bottle.abort(403, 'The last problem publish has already finished')
    publish_times = [next_publish_time]
    for _ in xrange(99):
        publish_time = publish_times[-1] + FLAGS.contest_primary_snapshot_interval
        if not settings.is_valid_publish_time(publish_time):
            break
        publish_times.append(publish_time)
    template_dict = {
        'publish_times': publish_times,
    }
    return handler_util.render('problem_submit.html', template_dict)


@bottle.post('/problem/submit')
@handler_util.require_login
def problem_submit_post_handler():
    if not settings.is_contest_running():
        bottle.abort(403, 'The contest is over!')
    if handler_util.get_current_user()['organizer']:
        bottle.abort(400, 'You are organizer, use API to submit problems.')
    handler_util.enforce_api_rate_limit(
        action='submission',
        limit_in_window=FLAGS.api_rate_limit_submissions_in_window)
    try:
        publish_time = int(bottle.request.forms['publish_time'])
        solution_spec = bottle.request.forms['solution_spec'].decode('ascii')
    except (KeyError, ValueError):
        bottle.abort(400, 'Invalid form.')
    else:
        if not settings.is_valid_publish_time(publish_time):
            bottle.abort(403, 'Invalid publish time.')
        if publish_time < misc_util.time():
            bottle.abort(403, 'Missed the publish time.')
    try:
        with eventlog.record_time('judge') as record:
            solution_spec, solution_size = game.normalize_solution(solution_spec)
            problem_spec, problem_size = game.compile_problem(solution_spec)
    except game.VerificationError as e:
        bottle.abort(400, 'Invalid solution spec: %s' % e.message)
    create_time = misc_util.time()
    if publish_time < create_time:
        bottle.abort(403, 'Missed the publish time.')
    new_problem = model.enqueue_problem(
        owner=handler_util.get_current_username(),
        problem_spec=problem_spec,
        problem_size=problem_size,
        solution_spec=solution_spec,
        solution_size=solution_size,
        create_time=create_time,
        publish_time=publish_time,
        processing_time=record['processing_time'],
        publish_immediately=False)
    template_dict = {
        'problem': new_problem,
        'problem_spec': problem_spec,
        'solution_spec': solution_spec,
    }
    return handler_util.render('problem_submitted.html', template_dict)


@bottle.get('/solution/submit')
@handler_util.require_login
def solution_submit_handler():
    if handler_util.get_current_user()['organizer']:
        bottle.abort(400, 'You are organizer, not allowed to submit solutions.')
    problem_id = bottle.request.query.get('problem_id', '')
    return handler_util.render('solution_submit.html', {'problem_id': problem_id})


@bottle.post('/solution/submit')
@handler_util.require_login
def solution_submit_post_handler():
    if not settings.is_contest_running():
        bottle.abort(403, 'The contest is over!')
    if handler_util.get_current_user()['organizer']:
        bottle.abort(400, 'You are organizer, not allowed to submit solutions.')
    handler_util.enforce_api_rate_limit(
        action='submission',
        limit_in_window=FLAGS.api_rate_limit_submissions_in_window)
    try:
        problem_id = int(bottle.request.forms['problem_id'])
        solution_spec = bottle.request.forms['solution_spec']
    except (KeyError, ValueError):
        bottle.abort(400, 'Invalid form.')
    try:
        problem = model.get_public_problem(problem_id=problem_id)
    except KeyError:
        bottle.abort(404, 'Problem not found.')
    username = handler_util.get_current_username()
    if username == problem['owner']:
        bottle.abort(403, 'Can not submit a solution to an own problem.')
    problem_spec_hash = problem['problem_spec_hash']
    problem_spec = model.load_blob(problem_spec_hash)
    try:
        with eventlog.record_time('judge') as record:
            solution_spec, solution_size = game.normalize_solution(solution_spec)
            resemblance_int, raw_evaluator_output = game.evaluate_solution(
                problem_spec, solution_spec)
    except game.VerificationError as e:
        bottle.abort(400, 'Invalid solution spec: %s' % e.message)
    new_solution = model.register_solution(
        owner=username,
        problem_id=problem_id,
        problem_spec_hash=problem_spec_hash,
        solution_spec=solution_spec,
        solution_size=solution_size,
        resemblance_int=resemblance_int,
        processing_time=record['processing_time'])
    template_dict = {
        'solution': new_solution,
        'solution_spec': solution_spec,
    }
    return handler_util.render('solution_submitted.html', template_dict)


@bottle.get('/leaderboard')
def leaderboard_handler():
    snapshot_time, ranking = model.get_last_leaderboard_snapshot(public_only=True)
    team_display_name_map = handler_util.compute_team_display_name_map(
        entry['username'] for entry in ranking)

    sushify_mode = get_sushify_mode()
    for entry in ranking:
        entry["score"] = sushify(sushify_mode, '%.1f' % entry["score"])

    template_dict = {
        'snapshot_time': snapshot_time,
        'ranking': ranking,
        'team_display_name_map': team_display_name_map,
        'sushify_mode': sushify_mode,
    }
    return handler_util.render('leaderboard.html', template_dict)


@bottle.get('/apihelp')
@handler_util.require_login
def api_help_handler():
    template_dict = {
        'hostname': bottle.request.urlparts.hostname,
        'first_publish_time': FLAGS.contest_first_publish_time,
        'last_publish_time': FLAGS.contest_last_publish_time,
        'snapshot_interval': FLAGS.contest_primary_snapshot_interval,
        'api_rate_limit_submissions_in_window': FLAGS.api_rate_limit_submissions_in_window,
        'api_rate_limit_blob_lookups_in_window': FLAGS.api_rate_limit_blob_lookups_in_window,
    }
    return handler_util.render('api_help.html', template_dict)


@bottle.route('/api/hello', method=['GET', 'POST'])
@handler_util.json_api_handler
def api_hello_handler():
    handler_util.enforce_api_rate_limit(
        action='hello',
        limit_in_window=1000)
    return {'greeting': 'Hello, world!'}


@bottle.get('/api/snapshot/list')
@handler_util.json_api_handler
def api_snapshot_list_handler():
    handler_util.enforce_api_rate_limit(
        action='snapshot_list',
        limit_in_window=1000)
    contest_snapshots = model.get_public_contest_snapshots()
    response = {
        'snapshots': [
            {
                'snapshot_time': snapshot['snapshot_time'],
                'snapshot_hash': snapshot['snapshot_hash'],
            }
            for snapshot in contest_snapshots
        ],
    }
    return response


@bottle.post('/api/problem/submit')
@handler_util.json_api_handler
def api_problem_submit_handler():
    # HACK: Allow problem submissions before the contest for organizers.
    if settings.has_contest_finished():
        bottle.abort(403, 'The contest is over!')
    handler_util.enforce_api_rate_limit(
        action='submission',
        limit_in_window=FLAGS.api_rate_limit_submissions_in_window)
    organizer = handler_util.get_current_user()['organizer']
    if organizer:
        if 'organizer' not in bottle.request.forms:
            bottle.abort(400, 'You are organizer, send organizer param.')
    try:
        solution_spec = handler_util.get_post_param('solution_spec').decode('ascii')
    except KeyError:
        bottle.abort(400, 'solution_spec is not set.')
    except ValueError:
        bottle.abort(400, 'Invalid solution_spec.')
    if organizer:
        if 'publish_time' in bottle.request.forms:
            bottle.abort(400, 'You are organizer, publish_time is ignored.')
        publish_time = FLAGS.contest_start_time
    else:
        try:
            publish_time = int(bottle.request.forms['publish_time'])
        except KeyError:
            bottle.abort(400, 'publish_time is not set.')
        except ValueError:
            bottle.abort(403, 'Invalid publish_time.')
        if not settings.is_valid_publish_time(publish_time):
            bottle.abort(403, 'Invalid publish time.')
        if publish_time < misc_util.time():
            bottle.abort(403, 'Missed the publish time.')
    try:
        with eventlog.record_time('judge') as record:
            solution_spec, solution_size = game.normalize_solution(solution_spec)
            problem_spec, problem_size = game.compile_problem(solution_spec)
    except game.VerificationError as e:
        bottle.abort(400, 'Invalid solution spec: %s' % e.message)
    create_time = misc_util.time()
    if not organizer and publish_time < create_time:
        bottle.abort(403, 'Missed the publish time.')
    new_problem = model.enqueue_problem(
        owner=handler_util.get_current_username(),
        problem_spec=problem_spec,
        problem_size=problem_size,
        solution_spec=solution_spec,
        solution_size=solution_size,
        create_time=create_time,
        publish_time=publish_time,
        processing_time=record['processing_time'],
        publish_immediately=organizer)
    response = {
        'problem_id': new_problem['_id'],
        'publish_time': new_problem['publish_time'],
        'problem_spec_hash': new_problem['problem_spec_hash'],
        'problem_size': new_problem['problem_size'],
        'solution_spec_hash': new_problem['solution_spec_hash'],
        'solution_size': new_problem['solution_size'],
    }
    return response


@bottle.post('/api/solution/submit')
@handler_util.json_api_handler
def api_solution_submit_handler():
    if not settings.is_contest_running():
        bottle.abort(403, 'The contest is over!')
    if handler_util.get_current_user()['organizer']:
        bottle.abort(400, 'You are organizer, not allowed to submit solutions.')
    handler_util.enforce_api_rate_limit(
        action='submission',
        limit_in_window=FLAGS.api_rate_limit_submissions_in_window)
    try:
        problem_id = int(handler_util.get_post_param('problem_id'))
    except KeyError:
        bottle.abort(400, 'problem_id is not set.')
    except ValueError:
        bottle.abort(400, 'Invalid problem_id.')
    try:
        solution_spec = handler_util.get_post_param('solution_spec').decode('ascii')
    except KeyError:
        bottle.abort(400, 'solution_spec is not set.')
    except ValueError:
        bottle.abort(400, 'Invalid solution_spec.')
    try:
        problem = model.get_public_problem(problem_id=problem_id)
    except KeyError:
        bottle.abort(404, 'Problem not found.')
    username = handler_util.get_current_username()
    if username == problem['owner']:
        bottle.abort(403, 'Can not submit a solution to an own problem.')
    problem_spec_hash = problem['problem_spec_hash']
    problem_spec = model.load_blob(problem_spec_hash)
    if FLAGS.enable_load_test_hacks:
        if solution_spec.strip() == 'loadtest-trivial':
            solution_spec = misc_util.load_testdata('trivial.txt')
        elif solution_spec.strip() == 'loadtest-lambda':
            solution_spec = misc_util.load_testdata('lambda.txt')
    try:
        with eventlog.record_time('judge') as record:
            solution_spec, solution_size = game.normalize_solution(solution_spec)
            resemblance_int, raw_evaluator_output = game.evaluate_solution(
                problem_spec, solution_spec)
    except game.VerificationError as e:
        bottle.abort(400, 'Invalid solution spec: %s' % e.message)
    new_solution = model.register_solution(
        owner=username,
        problem_id=problem_id,
        problem_spec_hash=problem_spec_hash,
        solution_spec=solution_spec,
        solution_size=solution_size,
        resemblance_int=resemblance_int,
        processing_time=record['processing_time'])
    response = {
        'problem_id': new_solution['problem_id'],
        'solution_spec_hash': new_solution['solution_spec_hash'],
        'solution_size': new_solution['solution_size'],
        'resemblance': new_solution['resemblance_int'] / 1000000.0,
    }
    return response


@bottle.get('/api/blob/<hash>')
def api_blob_handler(hash):
    if not settings.is_contest_running():
        bottle.abort(403, 'The contest is over!')
    handler_util.enforce_api_rate_limit(
        action='blob_lookup',
        limit_in_window=FLAGS.api_rate_limit_blob_lookups_in_window)
    url = model.get_signed_blob_url(hash)
    if url:
        bottle.redirect(url)
    try:
        blob = model.load_blob(hash)
    except KeyError:
        bottle.abort(404, 'Blob not found')
    bottle.response.content_type = 'text/plain'
    return blob


@bottle.get('/admin/')
@handler_util.require_admin
def admin_index_handler():
    return handler_util.render('admin/index.html', {})


@bottle.get('/admin/user/list')
@handler_util.require_admin
def admin_user_list_handler():
    users = model.get_all_users()
    template_dict = {
        'users': users,
    }
    return handler_util.render('admin/user_list.html', template_dict)


@bottle.get('/admin/user/view/<username>')
@handler_util.require_admin
def admin_user_view_handler(username):
    user = model.get_user(username)
    problems = model.get_user_problems(username)
    solutions = model.get_user_solutions(username)
    statistics = calculate_statistics_for_user(user, problems, solutions)
    template_dict = {
        'user': user,
        'problems': problems,
        'solutions': solutions,
        'statistics': statistics,
    }
    return handler_util.render('admin/user_view.html', template_dict)


def calculate_statistics_for_user(user, problems, solutions):
    total_problem_score = 0.0
    problem_count = len(problems)
    public_problem_count = 0
    solution_count = len(solutions)
    perfect_solution_count = 0
    imperfect_solution_count = 0

    for problem in problems:
        if problem["public"]:
            public_problem_count += 1
            problem_score = float(5000 - problem["solution_size"]) / (problem["perfect_solution_count"] + 1)
            problem["problem_score"] = problem_score
            total_problem_score += problem_score
    for solution in solutions:
        if solution["resemblance_int"] == 1000000:
            perfect_solution_count += 1
        else:
            imperfect_solution_count += 1

    score = {
        "public_problem_count": public_problem_count,
        "problem_count": problem_count,
        "total_problem_score": total_problem_score,
        "solution_count": solution_count,
        "perfect_solution_count": perfect_solution_count,
        "imperfect_solution_count": imperfect_solution_count,
    }

    return score


@bottle.get('/admin/problem/list')
@handler_util.require_admin
def admin_problem_list_handler():
    page = int(bottle.request.query.get('page', 1))
    count = model.count_all_problems_for_admin()
    problems = model.get_all_problems_for_admin(
        limit=FLAGS.pagination_items_per_page,
        skip=(page - 1) * FLAGS.pagination_items_per_page)
    team_display_name_map = handler_util.compute_team_display_name_map(
        problem['owner'] for problem in problems)
    pagination = handler_util.Pagination(
        page, FLAGS.pagination_items_per_page, count)
    template_dict = {
        'problems': problems,
        'team_display_name_map': team_display_name_map,
        'pagination': pagination,
    }
    return handler_util.render('admin/problem_list.html', template_dict)


@bottle.get('/admin/problem/vislist')
@handler_util.require_admin
def admin_problem_vislist_handler():
    page = int(bottle.request.query.get('page', 1))
    count = model.count_all_problems_for_admin()
    problems = model.get_all_problems_for_admin(
        limit=30,
        skip=(page - 1) * 30)
    team_display_name_map = handler_util.compute_team_display_name_map(
        problem['owner'] for problem in problems)
    pagination = handler_util.Pagination(page, 30, count)
    template_dict = {
        'problems': problems,
        'team_display_name_map': team_display_name_map,
        'pagination': pagination,
    }
    return handler_util.render('admin/problem_vislist.html', template_dict)


@bottle.get('/admin/problem/view/<problem_id>')
@handler_util.require_admin
def admin_problem_view_handler(problem_id):
    problem_id = int(problem_id)
    try:
        problem = model.get_problem_for_admin(problem_id=problem_id)
    except KeyError:
        bottle.abort(404, 'Problem not found.')
    owner = model.get_user(problem['owner'])
    problem_spec = model.load_blob(problem['problem_spec_hash'])
    snapshot_time, ranked_solutions = model.get_last_problem_ranking_snapshot(
        problem_id=problem_id, public_only=False)
    handler_util.inject_ranks_to_ranked_solutions(ranked_solutions)
    team_display_name_map = handler_util.compute_team_display_name_map(
        solution['owner'] for solution in ranked_solutions)
    template_dict = {
        'problem': problem,
        'problem_spec': problem_spec,
        'owner': owner,
        'ranked_solutions': ranked_solutions,
        'team_display_name_map': team_display_name_map,
        'snapshot_time': snapshot_time,
    }
    return handler_util.render('admin/problem_view.html', template_dict)


@bottle.get('/admin/solution/list')
@handler_util.require_admin
def admin_solution_list_handler():
    page = int(bottle.request.query.get('page', 1))
    count = model.count_all_solutions_for_admin()
    solutions = model.get_all_solutions_for_admin(
        limit=FLAGS.pagination_items_per_page,
        skip=(page - 1) * FLAGS.pagination_items_per_page)
    team_display_name_map = handler_util.compute_team_display_name_map(
        solution['owner'] for solution in solutions)
    pagination = handler_util.Pagination(
        page, FLAGS.pagination_items_per_page, count)
    template_dict = {
        'solutions': solutions,
        'team_display_name_map': team_display_name_map,
        'pagination': pagination,
    }
    return handler_util.render('admin/solution_list.html', template_dict)


@bottle.get('/admin/solution/view/<solution_id>')
@handler_util.require_admin
def admin_solution_view_handler(solution_id):
    solution_id = int(solution_id)
    try:
        solution = model.get_solution_for_admin(solution_id=solution_id)
        problem = model.get_problem_for_admin(problem_id=solution['problem_id'])
    except KeyError:
        bottle.abort(404, 'Solution not found.')
    problem_owner = model.get_user(problem['owner'])
    solution_owner = model.get_user(solution['owner'])
    solution_spec = model.load_blob(solution['solution_spec_hash'])
    template_dict = {
        'solution': solution,
        'solution_spec': solution_spec,
        'solution_owner': solution_owner,
        'problem_owner': problem_owner,
    }
    return handler_util.render('admin/solution_view.html', template_dict)


@bottle.get('/admin/leaderboard')
@handler_util.require_admin
def admin_leaderboard_handler():
    snapshot_time, ranking = model.get_last_leaderboard_snapshot(public_only=False)
    team_display_name_map = handler_util.compute_team_display_name_map(
        entry['username'] for entry in ranking)
    template_dict = {
        'snapshot_time': snapshot_time,
        'ranking': ranking,
        'team_display_name_map': team_display_name_map,
    }
    return handler_util.render('admin/leaderboard.html', template_dict)


@bottle.get('/admin/visualize/problem/<problem_id>')
@handler_util.require_admin
def admin_visualize_problem_handler(problem_id):
    thumbnail = bool(bottle.request.query.get('thumbnail'))
    problem_id = int(problem_id)
    try:
        problem = model.get_problem_for_admin(problem_id=problem_id)
    except KeyError:
        bottle.abort(404, 'Problem not found.')
    problem_spec = model.load_blob(problem['problem_spec_hash'])
    image_binary = visualize.visualize_problem(problem_spec, thumbnail)
    bottle.response.content_type = 'image/png'
    return image_binary


@bottle.get('/admin/visualize/solution/<solution_id>')
@handler_util.require_admin
def admin_visualize_solution_handler(solution_id):
    thumbnail = bool(bottle.request.query.get('thumbnail'))
    solution_id = int(solution_id)
    try:
        solution = model.get_solution_for_admin(solution_id=solution_id)
    except KeyError:
        bottle.abort(404, 'Solution not found.')
    solution_spec = model.load_blob(solution['solution_spec_hash'])
    problem_spec = model.load_blob(solution['problem_spec_hash'])
    image_binary = visualize.visualize_solution(
        problem_spec, solution_spec, thumbnail)
    bottle.response.content_type = 'image/png'
    return image_binary


@bottle.get('/testing/cron/snapshot_job')
def testing_cron_snapshot_job_handler():
    if not FLAGS.enable_testing_handlers:
        bottle.abort(403, 'Disabled')
    cron_jobs.snapshot_job()
    return 'done'
