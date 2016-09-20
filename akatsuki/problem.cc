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

#include "problem.h"

namespace akatsuki {

std::istream& operator>>(std::istream& is, ProblemSpec& spec) {
  int n;
  if (!(is >> n)) {
    return is;
  }
  spec.polygons.resize(n);
  for (int i = 0; i < n; ++i) {
    int m;
    if (!(is >> m)) {
      return is;
    }
    Polygon& polygon = spec.polygons[i];
    polygon.resize(m);
    for (int j = 0; j < m; ++j) {
      if (!(is >> polygon[j])) {
        return is;
      }
    }
  }
  int e;
  if (!(is >> e)) {
    return is;
  }
  spec.edges.resize(e);
  for (int i = 0; i < e; ++i) {
    Complex a, b;
    if (!(is >> a >> b)) {
      return is;
    }
    spec.edges[i] = Segment::FromEndpoints(a, b);
  }
  return is;
}

std::ostream& operator<<(std::ostream& os, const ProblemSpec& spec) {
  os << spec.polygons.size() << std::endl;
  for (const Polygon& polygon : spec.polygons) {
    os << polygon.size() << std::endl;
    for (const Complex& p : polygon) {
      os << p.real() << "," << p.imag() << std::endl;
    }
  }
  os << spec.edges.size() << std::endl;
  for (const Segment& edge : spec.edges) {
    const Complex to = edge.pos + edge.dir;
    os << edge.pos.real() << "," << edge.pos.imag() << " "
       << to.real() << "," << to.imag() << std::endl;
  }
  return os;
}

}  // namespace akatsuki
