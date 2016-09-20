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

SOLUTION_SIZE_LIMIT = 5000
PERFECT_RESEMBLANCE_INT = 1000000


def compute_team_scores_for_problem(problem, solutions):
    team_scores = {}
    num_perfects = 1 + sum(
        1 for solution in solutions
        if solution['resemblance_int'] == PERFECT_RESEMBLANCE_INT)
    team_scores[problem['owner']] = (
        float(SOLUTION_SIZE_LIMIT - problem['solution_size']) / num_perfects)
    solution_score_unit = float(problem['solution_size']) / num_perfects
    total_imperfect_resemblance = sum(
        solution['resemblance_int'] for solution in solutions
        if solution['resemblance_int'] < PERFECT_RESEMBLANCE_INT)
    for solution in solutions:
        if solution['resemblance_int'] == PERFECT_RESEMBLANCE_INT:
            team_scores[solution['owner']] = solution_score_unit
        elif solution['resemblance_int'] > 0:  # avoid zero division
            team_scores[solution['owner']] = (
                solution_score_unit *
                solution['resemblance_int'] / total_imperfect_resemblance)
    return team_scores
