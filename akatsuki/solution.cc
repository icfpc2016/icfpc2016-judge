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

#include "solution.h"

namespace akatsuki {

std::istream& operator>>(std::istream& is, SolutionSpec& spec) {
  int n;
  if (!(is >> n)) {
    return is;
  }
  spec.src_points.resize(n);
  for (int i = 0; i < n; ++i) {
    if (!(is >> spec.src_points[i])) {
      return is;
    }
  }
  int m;
  if (!(is >> m)) {
    return is;
  }
  spec.facet_defs.resize(m);
  for (int i = 0; i < m; ++i) {
    int k;
    if (!(is >> k)) {
      return is;
    }
    spec.facet_defs[i].resize(k);
    for (int j = 0; j < k; ++j) {
      if (!(is >> spec.facet_defs[i][j])) {
        return is;
      }
    }
  }
  spec.dst_points.resize(n);
  for (int i = 0; i < n; ++i) {
    if (!(is >> spec.dst_points[i])) {
      return is;
    }
  }
  spec.src_facets.resize(m);
  spec.dst_facets.resize(m);
  for (int i = 0; i < m; ++i) {
    spec.src_facets[i].resize(spec.facet_defs[i].size());
    spec.dst_facets[i].resize(spec.facet_defs[i].size());
    for (int j = 0; j < spec.facet_defs[i].size(); ++j) {
      spec.src_facets[i][j] = spec.src_points[spec.facet_defs[i][j]];
      spec.dst_facets[i][j] = spec.dst_points[spec.facet_defs[i][j]];
    }
  }
  return is;
}

}  // namespace akatsuki
