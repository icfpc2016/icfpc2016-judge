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

#ifndef AKATSUKI_SWEEP_H
#define AKATSUKI_SWEEP_H

#include <vector>

#include "geom.h"

namespace akatsuki {

// Computes a complex polygon from the union of polygons.
// Polygons with negative area are considered holes.
ComplexPolygon MakeComplexPolygon(const PolygonList& polygons);

// Computes the union of two complex polygons.
ComplexPolygon ComputeUnion(const ComplexPolygon& polygons1,
                            const ComplexPolygon& polygons2);

// Computes the intersection of two complex polygons.
ComplexPolygon ComputeIntersection(const ComplexPolygon& polygons1,
                                   const ComplexPolygon& polygons2);

}  // namespace akatsuki

#endif  // AKATSUKI_SWEEP_H
