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

#ifndef AKATSUKI_PROBLEM_H
#define AKATSUKI_PROBLEM_H

#include <iostream>
#include <vector>

#include "geom.h"

namespace akatsuki {

struct ProblemSpec {
  ComplexPolygon polygons;
  std::vector<Segment> edges;
};

std::istream& operator>>(std::istream& is, ProblemSpec& spec);
std::ostream& operator<<(std::ostream& os, const ProblemSpec& spec);

}  // namespace akatsuki

#endif  // AKATSUKI_PROBLEM_H
