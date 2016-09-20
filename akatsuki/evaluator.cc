// -*- mode: c++ -*-
//
// Copyright 2016 ICFP Programming Contest 2016 Organizers
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "evaluator.h"

#include <algorithm>
#include <cmath>
#include <iterator>
#include <iomanip>
#include <set>

#include <glog/logging.h>

#include "sweep.h"
#include "util.h"

namespace akatsuki {

int Evaluate(const ProblemSpec& problem_spec,
             const SolutionSpec& solution_spec) {
  const ComplexPolygon& problem_polygons = problem_spec.polygons;
  const ComplexPolygon solution_polygons =
      MakeComplexPolygon(MakeCounterclockwise(solution_spec.dst_facets));
  ComplexPolygon union_polygons =
      ComputeUnion(problem_polygons, solution_polygons);
  ComplexPolygon intersection_polygons =
      ComputeIntersection(problem_polygons, solution_polygons);
  Number union_area = ComputeSignedArea(union_polygons);
  Number intersection_area = ComputeSignedArea(intersection_polygons);
  Number resemblance = intersection_area / union_area;
  int resemblance_int = mpz_class(
      1000000 * resemblance.get_num() / resemblance.get_den()).get_si();
  return resemblance_int;
}

}  // namespace akatsuki
