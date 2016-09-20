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

import cStringIO

import matplotlib; matplotlib.use('Agg')
from matplotlib import patches
from matplotlib import path
from matplotlib import pyplot


_PROBLEM_COLOR = {'facecolor': '#798df7', 'edgecolor': '#31708f','alpha':0.3}
_SILHOUETTE_COLOR = {'facecolor': '#000000', 'edgecolor': '#0080ff', 'filled': False}
_SOLUTION_COLOR = {'facecolor': '#f27e7e', 'edgecolor': '#a94442'}


def _parse_fraction(text):
    if '/' in text:
        num, den = [float(s) for s in text.split('/')]
        return num / den
    return float(text)


def _parse_problem_spec(problem_spec):
    lines = problem_spec.splitlines()
    num_polygons = int(lines.pop(0))
    polygons = []
    for _ in xrange(num_polygons):
        num_vertices = int(lines.pop(0))
        polygon = []
        for _ in xrange(num_vertices):
            x, y = [_parse_fraction(s) for s in lines.pop(0).split(',')]
            polygon.append((x, y))
        polygons.append(polygon)
    segments = []
    num_segments = int(lines.pop(0))
    for _ in xrange(num_segments):
        line = lines.pop(0)
        ss, ts = line.split()
        sx, sy = [_parse_fraction(s) for s in ss.split(',')]
        tx, ty = [_parse_fraction(s) for s in ts.split(',')]
        segments.append((sx, sy, tx, ty))
    return polygons, segments


def _parse_solution_spec(solution_spec):
    lines = solution_spec.splitlines()
    num_points = int(lines.pop(0))
    lines = lines[num_points:]
    num_facets = int(lines.pop(0))
    facet_defs = []
    for _ in xrange(num_facets):
        facet_defs.append([int(s) for s in lines.pop(0).split()][1:])
    dst_points = []
    for _ in xrange(num_points):
        x, y = [_parse_fraction(s) for s in lines.pop(0).split(',')]
        dst_points.append((x, y))
    facets = []
    for facet_def in facet_defs:
        facets.append([dst_points[i] for i in facet_def])
    return facets


def _create_figure(polygons, thumbnail):
    fig = pyplot.figure(figsize=((1.4, 1.4) if thumbnail else (6, 6)))
    xs = [p[0] for polygon in polygons for p in polygon]
    ys = [p[1] for polygon in polygons for p in polygon]
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    radius = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.55
    axes = fig.gca(xlim=(cx - radius, cx + radius), ylim=(cy - radius, cy + radius))
    if thumbnail:
        axes.axis('off')
    else:
        axes.grid(color='gray', linestyle='--', linewidth=0.5)
    return fig


def _render_polygon(axes, polygons, segments, facecolor, edgecolor, filled=True,alpha=1.0):
    vertices = []
    codes = []
    for polygon in polygons:
        vertices.extend(polygon + [(0, 0)])
        codes.extend(
            [path.Path.MOVETO] +
            [path.Path.LINETO] * (len(polygon) - 1) +
            [path.Path.CLOSEPOLY])
    if vertices and filled:
        axes.add_patch(
            patches.PathPatch(path.Path(vertices, codes), facecolor=facecolor, alpha=alpha))
    linewidth = 1
    if not filled: linewidth = 3
    for sx, sy, tx, ty in segments:
        axes.plot(
            [sx, tx], [sy, ty],
            linewidth=linewidth, color=edgecolor, zorder=1)


def _save_figure(fig):
    buf = cStringIO.StringIO()
    fig.savefig(buf, format='png')
    return buf.getvalue()


def visualize_problem(problem_spec, thumbnail):
    polygons, segments = _parse_problem_spec(problem_spec)
    fig = _create_figure(polygons, thumbnail)
    _render_polygon(fig.gca(), polygons, segments, **_PROBLEM_COLOR)
    return _save_figure(fig)


def visualize_solution(problem_spec, solution_spec, thumbnail):
    problem_polygons, problem_segments = _parse_problem_spec(problem_spec)
    solution_facets = _parse_solution_spec(solution_spec)
    solution_segments = []

    problem_skeleton = []
    for p in problem_polygons:
        n = len(p)
        for i in range(n):
            j = (i+1)%n
            sx, sy = p[i]
            tx, ty = p[j]
            problem_skeleton.append((sx,sy,tx,ty))

    for facet in solution_facets:
        for (sx, sy), (tx, ty) in zip(facet, facet[1:] + [facet[0]]):
            solution_segments.append((sx, sy, tx, ty))
    fig = _create_figure(problem_polygons + solution_facets, thumbnail)
    for facet in solution_facets:
        _render_polygon(fig.gca(), [facet], [], **_SOLUTION_COLOR)
    _render_polygon(fig.gca(), [], solution_segments, **_SOLUTION_COLOR)
    _render_polygon(
        fig.gca(), problem_polygons, problem_segments, **_PROBLEM_COLOR)
    _render_polygon(
        fig.gca(), [], problem_skeleton, **_SILHOUETTE_COLOR)
    return _save_figure(fig)
