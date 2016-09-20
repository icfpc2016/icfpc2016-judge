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

#ifndef AKATSUKI_GEOM_H
#define AKATSUKI_GEOM_H

#include <complex>
#include <iostream>
#include <vector>

#include <gmpxx.h>

namespace akatsuki {

// Arbitrary precision fraction.
using Number = mpq_class;

// 2D point represented as a complex number.
using Complex = std::complex<Number>;

// Simple "signed" polygon represented as a vector of points. Usually points
// should be sorted in counterclockwise order and we say it is a
// "positive polygon". Otherwise, it is called a "negative polygon" and it
// will be considered as a hole when we compute union with other positive
// polygons.
using Polygon = std::vector<Complex>;

// Simple polygon represented as a vector of points. The order of points
// does not matter; it never represents a hole even if it is sorted in
// clockwise order, thus "unsigned".
using UnsignedPolygon = std::vector<Complex>;

// List of simple signed polygons. Polygons may overlap.
using PolygonList = std::vector<Polygon>;

// List of simple *positive* polygons. Negative polygons never appear.
// Any two polygons never share a point inside each of them.
using DisjointPolygonList = std::vector<Polygon>;

// Complex polygon which may have holes, represented as union of multiple
// simple polygons. Some polygons may overlap, but more constraints apply
// in addition to PolygonList: any three polygons never share a point inside
// each of them, and if two polygons share a point inside each of them, then
// those two polygons have different sign.
using ComplexPolygon = std::vector<Polygon>;

// List of simple unsigned polygons.
using UnsignedPolygonList = std::vector<UnsignedPolygon>;

// Represents a segment.
struct Segment {
  // Source point.
  Complex pos;
  // Destination point related to the source point.
  Complex dir;

  static Segment FromPosAndDir(const Complex& pos, const Complex& dir) {
    return Segment{pos, dir};
  }
  static Segment FromEndpoints(const Complex& a, const Complex& b) {
    return Segment{a, b - a};
  }
};

// Represents a line.
using Line = Segment;

// Allows comparing two points.
struct ComplexComparator {
  bool operator()(const Complex& a, const Complex& b) const {
    if (a.imag() != b.imag()) {
      return a.imag() < b.imag();
    }
    return a.real() < b.real();
  }
};

Number InnerProduct(const Complex& a, const Complex& b);
Number OuterProduct(const Complex& a, const Complex& b);
int Quadrant(const Complex& p);
bool LessAngle(const Complex& a, const Complex& b);

Number ComputeSignedArea(const Polygon& polygon);
Number ComputeSignedArea(const PolygonList& polygons);

bool LLIntersects(const Line& s, const Line& t, Complex* p);
bool SSIntersects(const Segment& s, const Segment& t);
bool SSIntersectsMiddle(const Segment& s, const Segment& t, Complex* p);
bool SPIntersectsMiddle(const Segment& s, const Complex& p);

PolygonList MakeCounterclockwise(const UnsignedPolygonList& polygons);
std::vector<Segment> SplitToSegments(const Polygon& polygon);
std::vector<Segment> SplitToSegments(const PolygonList& polygons);

std::vector<Segment> NormalizeSegmentDirection(const std::vector<Segment>& segments);
std::vector<Segment> ReverseSegments(const std::vector<Segment>& segments);
std::vector<Segment> MergeSegments(const std::vector<Segment>& segments);

std::istream& operator>>(std::istream& is, Complex& p);
std::ostream& operator<<(std::ostream& os, const Complex& p);
std::ostream& operator<<(std::ostream& os, const Polygon& polygon);

}  // namespace akatsuki

#endif  // AKATSUKI_GEOM_H
