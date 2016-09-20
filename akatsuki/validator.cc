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

#include "validator.h"

#include <algorithm>
#include <map>
#include <utility>
#include <vector>

#include <glog/logging.h>

#include "geom.h"
#include "sweep.h"

namespace akatsuki {

namespace {

std::vector<int> ComputeFacetSigns(const PolygonList& facets) {
  std::vector<int> signs;
  for (const Polygon& facet : facets) {
    signs.push_back(ComputeSignedArea(facet) > 0 ? 1 : -1);
  }
  return signs;
}

}  // namespace

bool ValidateSolution(const SolutionSpec& spec, bool check_normalized) {
  LOG(INFO) << "Validating solution...";

  // 0. All facets must have no less than 3 vertices.
  LOG(INFO) << "0. All facets must have no less than 3 vertices:";
  for (int index_facet = 0; index_facet < spec.facet_defs.size(); ++index_facet) {
    const std::vector<int>& facet_def = spec.facet_defs[index_facet];
    if (facet_def.size() < 3) {
      std::cout << "ValidateSolutionError: "
                << "Facet #" << index_facet << " must have no less than 3 vertices"
                << std::endl;
      LOG(INFO) << "failed.";
      return false;
    }
  }
  LOG(INFO) << "passed.";

  // 1. All source vertices must be in the unit square.
  LOG(INFO) << "1. All source vertices must be in the unit square:";
  for (const Complex& p : spec.src_points) {
    if (!(0 <= p.real() && p.real() <= 1 && 0 <= p.imag() && p.imag() <= 1)) {
      std::cout << "ValidateSolutionError: "
                << "Source vertex " << p << " is out of the unit square."
                << std::endl;
      LOG(INFO) << "failed.";
      return false;
    }
  }
  LOG(INFO) << "passed.";

  // 2. No dups in source vertices.
  LOG(INFO) << "2. No dups in source vertices:";
  {
    std::vector<Complex> ps(spec.src_points.begin(), spec.src_points.end());
    std::stable_sort(ps.begin(), ps.end(), ComplexComparator());
    if (std::unique(ps.begin(), ps.end()) != ps.end()) {
      std::cout << "ValidateSolutionError: "
                << "No coordinate should appear more than once in the source positions part."
                << std::endl;
      LOG(INFO) << "failed.";
      return false;
    }
  }
  LOG(INFO) << "passed.";

  // 3. No vertex in middle of facet edges.
  LOG(INFO) << "3. No vertex in middle of facet edges:";
  for (const Segment& edge : SplitToSegments(spec.src_facets)) {
    for (const Complex& p : spec.src_points) {
      if (SPIntersectsMiddle(edge, p)) {
        std::cout << "ValidateSolutionError: "
                  << "Vertex " << p << " must not lie on an edge."
                  << std::endl;
        LOG(INFO) << "failed.";
        return false;
      }
    }
  }
  LOG(INFO) << "passed.";

  // 4. All facets must be non-self-intersecting.
  LOG(INFO) << "4. All facets must be non-self-intersecting:";
  for (int index_facet = 0; index_facet < spec.src_facets.size(); ++index_facet) {
    const UnsignedPolygon& facet = spec.src_facets[index_facet];
    const std::vector<Segment> segments = SplitToSegments(facet);
    for (int i = 0; i < segments.size(); ++i) {
      for (int j = i + 2; j < segments.size(); ++j) {
        if (i == 0 && j == segments.size() - 1) {
          continue;
        }
        if (SSIntersects(segments[i], segments[j])) {
          std::cout << "ValidateSolutionError: "
                    << "Facet #" << index_facet << " must not intersect with itself."
                    << std::endl;
          LOG(INFO) << "failed.";
          return false;
        }
      }
    }
  }
  LOG(INFO) << "passed.";

  // 5. Polygons must be congruent.
  LOG(INFO) << "5. Polygons must be congruent:";
  for (int index_facet = 0; index_facet < spec.src_facets.size(); ++index_facet) {
    const std::vector<Segment> src_edges = SplitToSegments(spec.src_facets[index_facet]);
    const std::vector<Segment> dst_edges = SplitToSegments(spec.dst_facets[index_facet]);
    // All edges must have identical length.
    for (int i = 0; i < src_edges.size(); ++i) {
      if (std::norm(src_edges[i].dir) != std::norm(dst_edges[i].dir)) {
        std::cout << "ValidateSolutionError: "
                  << "Facet #" << index_facet << " is not mapped congruently."
                  << std::endl;
        LOG(INFO) << "failed.";
        return false;
      }
    }
    bool congruent = false;
    for (int mirror_sign : {1, -1}) {
      for (int i = 0; i < src_edges.size(); ++i) {
        int j = (i + 1) % src_edges.size();
        Number ip_src = InnerProduct(src_edges[i].dir, src_edges[j].dir);
        Number ip_dst = InnerProduct(dst_edges[i].dir, dst_edges[j].dir);
        if (ip_src != ip_dst) {
          goto try_mirror;
        }
        Number op_src = OuterProduct(src_edges[i].dir, src_edges[j].dir);
        Number op_dst = OuterProduct(dst_edges[i].dir, dst_edges[j].dir);
        if (op_src != op_dst * mirror_sign) {
          goto try_mirror;
        }
      }
      congruent = true;
      break;
     try_mirror:
      ;
    }
    if (!congruent) {
        std::cout << "ValidateSolutionError: "
                  << "Facet #" << index_facet << " is not mapped congruently."
                  << std::endl;
      LOG(INFO) << "failed.";
      return false;
    }
  }
  LOG(INFO) << "passed.";

  // 6. Facets must cover the unit square.
  LOG(INFO) << "6. Facets must cover the unit square:";
  {
    Number area_sum = ComputeSignedArea(MakeCounterclockwise(spec.src_facets));
    if (area_sum != 1) {
      std::cout << "ValidateSolutionError: "
                << "The sum of all facets area must be equal to 1. Current coverage area = " << area_sum
                << std::endl;

      LOG(INFO) << "failed.";
      LOG(INFO) << "total area = " << area_sum;
      return false;
    }
  }
  {
    ComplexPolygon union_polygons =
        MakeComplexPolygon(MakeCounterclockwise(spec.src_facets));
    Number area_sum = ComputeSignedArea(union_polygons);
    if (area_sum != 1) {
      std::cout << "ValidateSolutionError: "
                << "The union set of all facets at source positions must cover the unit square. Current coverage area = " << area_sum
                << std::endl;
      LOG(INFO) << "failed.";
      LOG(INFO) << "union area = " << area_sum;
      return false;
    }
  }
  LOG(INFO) << "passed.";

  if (check_normalized) {
    // 7. Adjacent facets in the source positions must have non-empty
    // intersection area in the destination positions.
    LOG(INFO) << "7. Adjacent facets in the source positions must have "
              << "non-empty intersection area in the destination positions.";
    std::map<std::pair<int, int>, std::vector<int>> adjacents;
    for (int index_facet = 0;
         index_facet < spec.facet_defs.size();
         ++index_facet) {
      const std::vector<int>& facet_def = spec.facet_defs[index_facet];
      for (int i = 0; i < facet_def.size(); ++i) {
        int j = (i + 1) % facet_def.size();
        int a = facet_def[i];
        int b = facet_def[j];
        adjacents[std::make_pair(std::min(a, b), std::max(a, b))].push_back(
            index_facet);
      }
    }
    std::vector<int> src_facet_signs = ComputeFacetSigns(spec.src_facets);
    std::vector<int> dst_facet_signs = ComputeFacetSigns(spec.dst_facets);
    for (const auto& entry : adjacents) {
      const std::vector<int>& facet_indices = entry.second;
      CHECK(facet_indices.size() <= 2);
      if (facet_indices.size() == 2) {
        int i = facet_indices[0];
        int j = facet_indices[1];
        if (src_facet_signs[i] * src_facet_signs[j] ==
            dst_facet_signs[i] * dst_facet_signs[j]) {
          std::cout << "ValidateSolutionError: "
                    << "Facet #" << i << " and #" << j << " must have non-empty intersection in the destination positions for the \"normalized\" requirement."
                    << std::endl;
          LOG(INFO) << "failed.";
          return false;
        }
      }
    }
    LOG(INFO) << "passed.";
  }

  return true;
}

}  // namespace akatsuki
