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

#include "sweep.h"

#include <algorithm>
#include <map>
#include <set>
#include <vector>

#include <glog/logging.h>

#include "util.h"

namespace akatsuki {

namespace {

struct Side {
  bool open;
  Number bottom_x;
  Number top_x;
  int color;
};

struct Ribbon {
  Number bottom_y, top_y;
  std::vector<Side> sides;
};

bool operator<(const Side& a, const Side& b) {
  if (a.bottom_x != b.bottom_x) {
    return a.bottom_x < b.bottom_x;
  }
  if (a.top_x != b.top_x) {
    return a.top_x < b.top_x;
  }
  // Visit open sides earlier than close sides to make trapezoids
  // as long as possible.
  return a.open > b.open;
}

void GetSidesWithinRange(
    const PolygonList& polygons,
    const Number bottom_y, const Number top_y, int color, std::vector<Side>* sides) {
  CHECK(bottom_y < top_y);
  const Line bottom_line = Line::FromPosAndDir(Complex(0, bottom_y), Complex(1, 0));
  const Line top_line = Line::FromPosAndDir(Complex(0, top_y), Complex(1, 0));
  for (const Segment& segment : SplitToSegments(polygons)) {
    if ((segment.pos.imag() >= top_y) !=
        ((segment.pos + segment.dir).imag() >= top_y)) {
      const bool open = (segment.pos.imag() >= top_y);
      Complex bottom_p, top_p;
      LLIntersects(segment, bottom_line, &bottom_p);
      LLIntersects(segment, top_line, &top_p);
      sides->push_back(Side{open, bottom_p.real(), top_p.real(), color});
    }
  }
}

std::vector<Number> EnumerateInterestingYCoordinates(
    const PolygonList& polygons) {
  std::set<Number> y_set;
  for (const Polygon& polygon : polygons) {
    for (const Complex& p : polygon) {
      y_set.insert(p.imag());
    }
  }
  const std::vector<Segment> segments = SplitToSegments(polygons);
  for (int i = 0; i < segments.size(); ++i) {
    for (int j = i + 1; j < segments.size(); ++j) {
      Complex p;
      if (SSIntersectsMiddle(segments[i], segments[j], &p)) {
        y_set.insert(p.imag());
      }
    }
  }
  return std::vector<Number>(y_set.begin(), y_set.end());
}

Polygon MakeTrapezoid(
    const Side& left_side, const Side& right_side,
    const Number bottom_y, const Number top_y) {
  Polygon trapezoid;
  trapezoid.push_back(Complex{left_side.bottom_x, bottom_y});
  if (left_side.bottom_x != right_side.bottom_x) {
    trapezoid.push_back(Complex{right_side.bottom_x, bottom_y});
  }
  trapezoid.push_back(Complex{right_side.top_x, top_y});
  if (left_side.top_x != right_side.top_x) {
    trapezoid.push_back(Complex{left_side.top_x, top_y});
  }
  return trapezoid;
}

std::vector<Ribbon> ComputeRibbons(
    const std::map<int, PolygonList>& color_to_polygons) {
  std::vector<Number> y_list;
  {
    PolygonList all_polygons;
    for (const std::pair<int, PolygonList>& entry : color_to_polygons) {
      all_polygons.insert(
          all_polygons.end(), entry.second.begin(), entry.second.end());
    }
    y_list = EnumerateInterestingYCoordinates(all_polygons);
  }
  std::vector<Ribbon> ribbons;
  for (int index_y = 0; index_y + 1 < y_list.size(); ++index_y) {
    Ribbon ribbon;
    ribbon.bottom_y = y_list[index_y];
    ribbon.top_y = y_list[index_y + 1];
    for (const std::pair<int, PolygonList>& entry : color_to_polygons) {
      GetSidesWithinRange(
          entry.second, ribbon.bottom_y, ribbon.top_y, entry.first,
          &ribbon.sides);
    }
    std::stable_sort(ribbon.sides.begin(), ribbon.sides.end());
    ribbons.push_back(std::move(ribbon));
  }
  return ribbons;
}

struct DirComparator {
  DirComparator(const Complex& base) : base_(base) {}
  bool operator()(const Segment& a, const Segment& b) const {
    return LessAngle(a.dir / base_, b.dir / base_);
  }
  Complex base_;
};

ComplexPolygon WalkSegments(const std::vector<Segment>& segments) {
  std::map<Complex, std::vector<Segment>, ComplexComparator> edges_map;
  for (const Segment& s : segments) {
    edges_map[s.pos].push_back(s);
  }
  ComplexPolygon polygons;
  while (!edges_map.empty()) {
    Polygon polygon;
    const Complex start_vertex = edges_map.begin()->first;
    Segment current_edge =
        Segment::FromEndpoints(start_vertex - Complex(1, 0), start_vertex);
    for (;;) {
      const Complex next_vertex = current_edge.pos + current_edge.dir;
      auto edges_iter = edges_map.find(next_vertex);
      if (edges_iter == edges_map.end()) {
        break;
      }
      std::vector<Segment>& edges = edges_iter->second;
      std::vector<Segment>::iterator edge_iter =
          std::min_element(edges.begin(), edges.end(),
                           DirComparator(-current_edge.dir));
      current_edge = *edge_iter;
      edges.erase(edge_iter);
      if (edges.empty()) {
        edges_map.erase(edges_iter);
      }
      polygon.push_back(current_edge.pos);
    }
    polygons.push_back(std::move(polygon));
  }
  return polygons;
}

ComplexPolygon MergeDisjointPolygons(const DisjointPolygonList& polygons) {
  return WalkSegments(MergeSegments(SplitToSegments(polygons)));
}

}  // namespace

ComplexPolygon MakeComplexPolygon(const PolygonList& polygons) {
  const std::vector<Ribbon> ribbons = ComputeRibbons({{1, polygons}});
  DisjointPolygonList trapezoids;
  for (const Ribbon& ribbon : ribbons) {
    int level = 0;
    const Side* left_side = nullptr;
    for (const Side& side : ribbon.sides) {
      if (side.open) {
        if (level == 0) {
          left_side = &side;
        }
        ++level;
      } else {
        CHECK(level > 0);
        --level;
        if (level == 0) {
          trapezoids.push_back(
              MakeTrapezoid(*left_side, side, ribbon.bottom_y, ribbon.top_y));
          left_side = nullptr;
        }
      }
    }
    CHECK(level == 0);
  }
  return MergeDisjointPolygons(trapezoids);
}

ComplexPolygon ComputeUnion(const ComplexPolygon& polygons1,
                            const ComplexPolygon& polygons2) {
  return MakeComplexPolygon(Concat(polygons1, polygons2));
}

ComplexPolygon ComputeIntersection(const ComplexPolygon& polygons1,
                                   const ComplexPolygon& polygons2) {
  const std::vector<Ribbon> ribbons =
      ComputeRibbons({{1, polygons1}, {2, polygons2}});
  DisjointPolygonList trapezoids;
  for (const Ribbon& ribbon : ribbons) {
    int levels[3] = {283, 0, 0};
    const Side* left_side = nullptr;
    for (const Side& side : ribbon.sides) {
      int& level = levels[side.color];
      if (side.open) {
        ++level;
        if (level == 1 && levels[1] >= 1 && levels[2] >= 1) {
          left_side = &side;
        }
      } else {
        CHECK(level > 0);
        if (level == 1 && levels[1] >= 1 && levels[2] >= 1) {
          trapezoids.push_back(
              MakeTrapezoid(*left_side, side, ribbon.bottom_y, ribbon.top_y));
          left_side = nullptr;
        }
        --level;
      }
    }
    CHECK(levels[1] == 0 && levels[2] == 0);
  }
  return MergeDisjointPolygons(trapezoids);
}

}  // namespace akatsuki
