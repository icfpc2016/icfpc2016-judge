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

#include "geom.h"

#include <algorithm>
#include <map>

#include <glog/logging.h>

namespace akatsuki {

Number InnerProduct(const Complex& a, const Complex& b) {
  return a.real() * b.real() + a.imag() * b.imag();
}

Number OuterProduct(const Complex& a, const Complex& b) {
  return a.real() * b.imag() - a.imag() * b.real();
}

int Quadrant(const Complex& p) {
  CHECK(!(p.real() == 0 && p.imag() == 0));
  if (p.real() > 0 && p.imag() >= 0) {
    return 1;
  } else if (p.real() <= 0 && p.imag() > 0) {
    return 2;
  } else if (p.real() < 0 && p.imag() <= 0) {
    return 3;
  }
  return 4;
}

bool LessAngle(const Complex& a, const Complex& b) {
  int qa = Quadrant(a);
  int qb = Quadrant(b);
  if (qa != qb) {
    return qa < qb;
  }
  return OuterProduct(a, b) > 0;
}

Number ComputeSignedArea(const Polygon& polygon) {
  Number area = 0;
  for (int i = 0; i < polygon.size(); ++i) {
    int j = (i + 1) % polygon.size();
    area += OuterProduct(polygon[i], polygon[j]) / 2;
  }
  return area;
}

Number ComputeSignedArea(const PolygonList& polygons) {
  Number area = 0;
  for (const Polygon& polygon : polygons) {
    area += ComputeSignedArea(polygon);
  }
  return area;
}

bool LLIntersects(const Line& s, const Line& t, Complex* p) {
  if (OuterProduct(s.dir, t.dir) == 0) {
    return false;
  }
  if (p != nullptr) {
    Number rs = OuterProduct(t.dir, t.pos - s.pos) / OuterProduct(t.dir, s.dir);
    *p = s.pos + s.dir * rs;
  }
  return true;
}

static int CCW(const Complex& p, const Complex& r, const Complex& s) {
  const Complex a = r - p, b = s - p;
  const Number op = OuterProduct(a, b);
  const int sgn = op > 0 ? 1 : op < 0 ? -1 : 0;
  if (sgn != 0) {
    return sgn;
  }
  if (a.real() * b.real() < 0 || a.imag() * b.imag() < 0) {
    return -1;
  }
  if (std::norm(a) < std::norm(b)) {
    return 1;
  }
  return 0;
}

bool SSIntersects(const Segment& s, const Segment& t) {
  return (CCW(s.pos, s.pos + s.dir, t.pos) *
          CCW(s.pos, s.pos + s.dir, t.pos + t.dir) <= 0 &&
          CCW(t.pos, t.pos + t.dir, s.pos) *
          CCW(t.pos, t.pos + t.dir, s.pos + s.dir) <= 0);
}

bool SSIntersectsMiddle(const Segment& s, const Segment& t, Complex* p) {
  if (OuterProduct(s.dir, t.dir) == 0) {
    return false;
  }
  Number rs = OuterProduct(t.dir, t.pos - s.pos) / OuterProduct(t.dir, s.dir);
  Number rt = OuterProduct(s.dir, s.pos - t.pos) / OuterProduct(s.dir, t.dir);
  if (!(0 < rs && rs < 1 && 0 < rt && rt < 1)) {
    return false;
  }
  if (p != nullptr) {
    *p = s.pos + s.dir * rs;
  }
  return true;
}

bool SPIntersectsMiddle(const Segment& s, const Complex& p) {
  Complex diff = p - s.pos;
  if (OuterProduct(s.dir, diff) != 0) {
    return false;
  }
  Number ip = InnerProduct(s.dir, diff);
  return (0 < ip && ip < InnerProduct(s.dir, s.dir));
}

PolygonList MakeCounterclockwise(const UnsignedPolygonList& polygons) {
  PolygonList ccw_polygons(polygons.begin(), polygons.end());
  for (Polygon& polygon : ccw_polygons) {
    if (ComputeSignedArea(polygon) < 0) {
      std::reverse(polygon.begin(), polygon.end());
    }
  }
  return ccw_polygons;
}

std::vector<Segment> SplitToSegments(const Polygon& polygon) {
  std::vector<Segment> segments;
  for (int i = 0; i < polygon.size(); ++i) {
    int j = (i + 1) % polygon.size();
    segments.push_back(Segment::FromEndpoints(polygon[i], polygon[j]));
  }
  return segments;
}

std::vector<Segment> SplitToSegments(const PolygonList& polygons) {
  std::vector<Segment> segments;
  for (const Polygon& polygon : polygons) {
    for (int i = 0; i < polygon.size(); ++i) {
      int j = (i + 1) % polygon.size();
      segments.push_back(Segment::FromEndpoints(polygon[i], polygon[j]));
    }
  }
  return segments;
}

namespace {

struct LineComparator {
  bool operator()(const Segment& a, const Segment& b) const {
    Complex pa = ClosestPointToOrigin(a);
    Complex pb = ClosestPointToOrigin(b);
    if (pa != pb) {
      return ComplexComparator()(pa, pb);
    }
    // Both lines go through the origin.
    Complex da = a.dir * Complex(Quadrant(a.dir) >= 3 ? -1 : 1, 0);
    Complex db = b.dir * Complex(Quadrant(b.dir) >= 3 ? -1 : 1, 0);
    return OuterProduct(da, db) > 0;
  }
  static Complex ClosestPointToOrigin(const Line& s) {
    return s.pos - s.dir * Complex(InnerProduct(s.pos, s.dir) / std::norm(s.dir));
  }
};

}  // namespace

std::vector<Segment> NormalizeSegmentDirection(const std::vector<Segment>& segments) {
  std::vector<Segment> new_segments(segments.begin(), segments.end());
  for (Segment& s : new_segments) {
    if (Quadrant(s.dir) >= 3) {
      s = Segment::FromPosAndDir(s.pos + s.dir, -s.dir);
    }
  }
  return new_segments;
}

std::vector<Segment> ReverseSegments(const std::vector<Segment>& segments) {
  std::vector<Segment> new_segments(segments.begin(), segments.end());
  for (Segment& s : new_segments) {
    s = Segment::FromPosAndDir(s.pos + s.dir, -s.dir);
  }
  return new_segments;
}

std::vector<Segment> MergeSegments(const std::vector<Segment>& segments) {
  std::map<Segment, std::vector<Segment>, LineComparator> lines;
  for (const Segment& s : segments) {
    lines[s].push_back(s);
  }
  std::vector<Segment> merged_segments;
  for (const std::pair<Segment, std::vector<Segment>>& entry : lines) {
    const std::vector<Segment>& segments_on_line = entry.second;
    std::map<Complex, int, ComplexComparator> events;
    for (const Segment& s : segments_on_line) {
      events[s.pos] += 1;
      events[s.pos + s.dir] -= 1;
    }
    int level = 0;
    Complex start;
    for (const std::pair<Complex, int>& event : events) {
      const Complex& cur = event.first;
      int delta = event.second;
      if (level > 0 && level + delta <= 0) {
        merged_segments.push_back(Segment::FromEndpoints(start, cur));
      } else if (level < 0 && level + delta >= 0) {
        merged_segments.push_back(Segment::FromEndpoints(cur, start));
      }
      if ((level >= 0 && level + delta < 0) ||
          (level <= 0 && level + delta > 0)) {
        start = cur;
      }
      level += delta;
    }
  }
  return merged_segments;
}

std::istream& operator>>(std::istream& is, Complex& p) {
  Number x, y;
  if (!(is >> x)) {
    return is;
  }
  if (is.peek() != ',') {
    is.setstate(std::ios_base::failbit);
    return is;
  }
  is.get();
  if (!(is >> y)) {
    return is;
  }
  x.canonicalize();
  y.canonicalize();
  p = Complex(x, y);
  return is;
}

std::ostream& operator<<(std::ostream& os, const Complex& p) {
  return os << "(" << p.real() << ", " << p.imag() << ")";
}

std::ostream& operator<<(std::ostream& os, const Polygon& polygon) {
  os << "[";
  bool first = true;
  for (const Complex& p : polygon) {
    if (!first) {
      os << ", ";
    }
    os << p;
    first = false;
  }
  os << "]";
  return os;
}

}  // namespace akatsuki
