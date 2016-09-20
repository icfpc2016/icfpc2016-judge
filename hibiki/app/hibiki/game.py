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

import re
import tempfile

import gflags
import subprocess32 as subprocess

FLAGS = gflags.FLAGS

_MAX_SOLUTION_SIZE = 5000

_JUDGE_TIMEOUT_SECONDS = 30

_NUMBER_RE = re.compile(
    r'^'
    r'(0|-?[1-9][0-9]*|((0|-?[1-9][0-9]*)/[1-9][0-9]*))'
    r'$'
)
_POINT_RE = re.compile(
    r'^'
    r'(0|-?[1-9][0-9]*|((0|-?[1-9][0-9]*)/[1-9][0-9]*))'
    r','
    r'(0|-?[1-9][0-9]*|((0|-?[1-9][0-9]*)/[1-9][0-9]*))'
    r'$'
)
_VERIFICATION_ERROR_RE = re.compile(r'^ValidateSolutionError:\s*(.*)$', re.MULTILINE)


class VerificationError(Exception):
    def __init__(self, message):
        super(VerificationError, self).__init__(message)
        self.message = message


def make_temporary_file_with_content(content):
    f = tempfile.NamedTemporaryFile()
    f.write(content)
    f.flush()
    f.seek(0)
    return f


def normalize_solution(solution_spec):
    """Normalizes a solution spec.

    Args:
        solution_spec: Specification string of a solution.

    Returns:
        (solution_spec, solution_size)
        solution_spec: Normalized specification string of a solution.
        solution_size: Solution size.

    Raises:
        VerificationError: When parsing failed.
    """
    new_solution_spec = ''
    tokens = solution_spec.split()

    try:
        num_points = int(tokens.pop(0))
    except Exception:
        raise VerificationError('Parse error in the number of source vertices.')
    if num_points <= 0:
        raise VerificationError('Number of source vertices must be positive.')
    new_solution_spec += '%d\n' % num_points

    for i in xrange(num_points):
        try:
            point = tokens.pop(0)
        except Exception:
            raise VerificationError('Parse error in coordinate of source vertex #%d.' % i)
        if not _POINT_RE.search(point):
            raise VerificationError('Parse error in coordinate of source vertex #%d.' % i)
        new_solution_spec += '%s\n' % point

    try:
        num_facets = int(tokens.pop(0))
    except Exception:
        raise VerificationError('Parse error in the number of facets.')
    if num_facets <= 0:
        raise VerificationError('Number of facets must be positive.')
    new_solution_spec += '%d\n' % num_facets

    for i in xrange(num_facets):
        try:
            facet_size = int(tokens.pop(0))
        except Exception:
            raise VerificationError('Parse error in the size of facet #%d.' % i)
        if facet_size < 3:
            raise VerificationError('The size of facet #%d must be no less than three.' % i)

        facet_def = []
        for j in xrange(facet_size):
            try:
                point_index = int(tokens.pop(0))
            except Exception:
                raise VerificationError('A vertex index in facet #%d is invalid.' % i)
            if not 0 <= point_index < num_points:
                raise VerificationError('A vertex index in facet #%d is out of range.' % i)
            facet_def.append(point_index)

        if len(set(facet_def)) != facet_size:
            raise VerificationError('Facet #%d has duplicated vertices.' % i)

        new_solution_spec += '%d %s\n' % (
            facet_size,
            ' '.join('%d' % facet_index for facet_index in facet_def))

    for i in xrange(num_points):
        try:
            point = tokens.pop(0)
        except Exception:
            raise VerificationError('Parse error in coordinate of destination vertex #%d.' % i)
        if not _POINT_RE.search(point):
            raise VerificationError('Parse error in coordinate of destination vertex #%d.' % i)
        new_solution_spec += '%s\n' % point

    if tokens:
        raise VerificationError('Redundant tokens found after the end of the specification.')

    solution_size = sum(len(s) for s in new_solution_spec.split())
    if solution_size > _MAX_SOLUTION_SIZE:
        raise VerificationError('Solution size limit exceeded.')

    return (new_solution_spec, solution_size)


def compile_problem(solution_spec):
    """Compiles a problem submission and generates a problem spec.

    Args:
        solution_spec: Specification string of a solution corresponding to the
            submitted problem.

    Returns:
        (problem_spec, problem_size)
        problem_spec: Specification string of the problem.
        problem_size: Problem size.

    Raises:
        VerificationError: If the solution specification is invalid.
        subprocess.TimeoutExpired: On judge timeout.
        AssertionError: On scrape error.
    """
    with make_temporary_file_with_content(solution_spec) as solution_file:
        proc = subprocess.Popen(
            ['./akatsuki', '--logtostderr', '--compile', solution_file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            stdout_output, stderr_output = proc.communicate(
                timeout=_JUDGE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise  # report ISE
    if proc.returncode:
        m = _VERIFICATION_ERROR_RE.search(stdout_output)
        assert m, stdout_output  # report ISE
        raise VerificationError(m.group(1))
    problem_spec = stdout_output
    problem_size = sum(len(s) for s in problem_spec.split())
    return (problem_spec, problem_size)


def evaluate_solution(problem_spec, solution_spec):
    """Evaluates a solution submission.

    Args:
        problem_spec: Specification string of a problem.
        solution_spec: Specification string of a solution.

    Returns:
        (resemblance_int, raw_evaluator_output)

    Raises:
        VerificationError: If any of the specifications are invalid.
        subprocess.TimeoutExpired: On judge timeout.
        AssertionError: On scrape error.
    """
    with make_temporary_file_with_content(problem_spec) as problem_file, \
         make_temporary_file_with_content(solution_spec) as solution_file:
        proc = subprocess.Popen(
            ['./akatsuki', '--logtostderr', '--evaluate',
             problem_file.name, solution_file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            stdout_output, stderr_output = proc.communicate(
                timeout=_JUDGE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise  # report ISE
    if proc.returncode:
        m = _VERIFICATION_ERROR_RE.search(stdout_output)
        assert m, stdout_output  # report ISE
        raise VerificationError(m.group(1))
    m = re.search(r'integer_resemblance: (\d+)', stdout_output)
    assert m, stdout_output  # report ISE
    resemblance_int = int(m.group(1))
    return resemblance_int, stdout_output.decode('utf-8')
