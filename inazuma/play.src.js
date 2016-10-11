function fold(l, z, f) {
    for (var i = 0; i < l.length; i++) z = f(z, l[i]);
    return z;
}

function push(l, x) {
    l = l.concat();
    l.push(x);
    return l;
}

function literal(s) { return s; }

// this definition will be removed
(function(root) {
    "use strict";

    function Complex(re, im) {
	this["re"] = re;
	this["im"] = im;
    }
    root['Complex'] = Complex;

    function Point(src, dst) {
	this["src"] = src;
	this["dst"] = dst;
    }
    root['Point'] = Point;

    function Facet(front, points) {
	this["front"] = front;
	this["points"] = points;
    }
    root['Facet'] = Facet;
})(this);

function fold2(l, z, f) {
    z = fold(l, [z], function(z, v) {
	return [z[1] ? f(z[0], z[1], v) : z[0], v];
    });
    return f(z[0], z[1], l[0]);
}

function map(l, f) {
    return fold(l, [], function(z, v) { return push(z, f(v)); });
}

function each(l, f) {
    fold(l,0,function(z,v){f(v);});
}

function add(a, b) {
    return new Complex(a.re + b.re, a.im + b.im);
}

function sub(a, b) {
    return new Complex(a.re - b.re, a.im - b.im);
}

function mul(a, b) {
    return new Complex(
	a.re * b.re - a.im * b.im,
	a.re * b.im + a.im * b.re
    );
}

function div(a, b) {
    var den = b.re * b.re + b.im * b.im;
    return new Complex(
	(b.re * a.re + b.im * a.im) / den,
	(b.re * a.im - b.im * a.re) / den
    );
}

function conj(a) {
    return new Complex(a.re, -a.im);
}

function flip_c(a) {
    return new Complex(1 - a.re, a.im);
}

// problem definition
function c(x, y) { return new Complex(x, y); }var problems = {"problem1":{"polygons":[[c(0.0,0.0),c(1.0,0.0),c(1.0,1.0),c(0.0,1.0)]],"holes":[],"segments":[[c(0.0,1.0),c(0.0,0.0)],[c(1.0,0.0),c(1.0,1.0)],[c(0.0,0.0),c(1.0,0.0)],[c(1.0,1.0),c(0.0,1.0)]]},"problem2":{"polygons":[[c(0.0,0.0),c(1.0,0.0),c(0.5,0.5),c(0.0,0.5)]],"holes":[],"segments":[[c(0.5,0.5),c(0.0,0.0)],[c(0.0,0.0),c(1.0,0.0)],[c(1.0,0.0),c(0.5,0.5)],[c(0.5,0.5),c(0.0,0.5)],[c(0.0,0.5),c(0.0,0.0)]]},"problem3":{"polygons":[[c(0.0,0.125),c(0.125,0.0),c(0.25,0.0),c(0.375,0.125),c(0.375,0.25),c(0.25,0.375),c(0.125,0.375),c(0.0,0.25)]],"holes":[[c(0.125,0.125),c(0.125,0.25),c(0.25,0.25),c(0.25,0.125)]],"segments":[[c(0.375,0.125),c(0.0,0.125)],[c(0.125,0.0),c(0.25,0.0)],[c(0.125,0.375),c(0.0,0.25)],[c(0.25,0.375),c(0.125,0.375)],[c(0.25,0.0),c(0.375,0.125)],[c(0.0,0.25),c(0.0,0.125)],[c(0.375,0.25),c(0.25,0.375)],[c(0.0,0.25),c(0.375,0.25)],[c(0.375,0.25),c(0.375,0.125)],[c(0.25,0.0),c(0.25,0.375)],[c(0.125,0.0),c(0.125,0.375)],[c(0.0,0.125),c(0.125,0.0)]]}};

function get_dropdown_id(s) {
    return $(literal("#origami #") + s + literal(" li.active")).data(s + literal("-id"));
}

function draw_facets(facets, type) {
    var ctx = $(type == "dst" ? literal("#dst") : literal("#src"))[0].getContext("2d");
    ctx.clearRect(-1, -1, 3, 3);

    ctx.beginPath();
    ctx.lineWidth = 0.001;
    ctx.strokeStyle = literal("#000000");
    fold(literal(Array.apply(null, { length: 40 })), -10, function(z, v) {
	ctx.moveTo(-1, v = z/10);
	ctx.lineTo(3, v);
	ctx.moveTo(v, -1);
	ctx.lineTo(v, 3);
	return z+1;
    });
    ctx.stroke();

    // draw each facet
    each(facets, function(facet) {
	ctx.beginPath();
	var points = facet.points;
	each(points, function(p) { ctx.lineTo(p[type].re, p[type].im); });
	ctx.closePath();

	var texture_id = get_dropdown_id(literal("texture"));
	texture_id && (
            type == "dst" && facet.front ? (
		ctx.save(),
		ctx.clip(),

		ctx.translate(points[0].dst.re, points[0].dst.im),
		// facets: p0, points: p1
		facets = flip_c(points[0].src),
		points = div(sub(flip_c(points[1].src), facets), sub(points[1].dst, points[0].dst)),
		ctx.rotate(-Math.atan2(points.im, points.re)),
		ctx.translate(-facets.re, -facets.im),

		ctx.drawImage(imgs[texture_id - 1], 0, 0, 512, 512, 0, 0, 1, 1),
		ctx.restore()
            ):(
		ctx.fillStyle = literal("#cccccc"),
		ctx.fill()
            )
	);

	ctx.lineWidth = 0.003;
	ctx.strokeStyle = literal("#000000");
	ctx.stroke();
    });

    if (type == "dst") {
	var silhouette_id = get_dropdown_id(literal("silhouette"));
	if(silhouette_id = silhouette_id ? literal(problems)[silhouette_id] : null)
            ctx.beginPath(),
            each([silhouette_id.polygons, silhouette_id.holes], function(polygons) {
		each(polygons, function(polygon) {
                    each(polygon, function(p) {
			ctx.lineTo(p.re, p.im);
                    });
                    ctx.closePath();
		});
            }),
            ctx.fillStyle = literal("rgba(255,192,192,.8)"),
            ctx.fill(),

            ctx.beginPath(),
            each(silhouette_id.segments, function(segment) {
		ctx.moveTo(segment[0].re, segment[0].im);
		ctx.lineTo(segment[1].re, segment[1].im);
            }),
            ctx.lineWidth = 0.005,
            ctx.strokeStyle = literal("rgba(255,128,128,.8)"),
            ctx.stroke();
    }
}

function redraw(facets) {
    draw_facets(facets, "dst");
    draw_facets(facets, "src");
}


// initial square
var cur_state = [new Facet(false, [
    new Point(new Complex(0, 0), new Complex(0, 0)),
    new Point(new Complex(1, 0), new Complex(1, 0)),
    new Point(new Complex(1, 1), new Complex(1, 1)),
    new Point(new Complex(0, 1), new Complex(0, 1))
])], state_stack = [], flipped = 0, imgs = [];

function next_state(cp0, cp1, preview) {
    if (cp0) {
	// calculate a bisector (p0-p1) of line segment (cp0-cp1)
	var v = sub(cp1, cp0),
	tmp = div(add(cp0, cp1), new Complex(2, 0)),
	p0, p1;
	tmp = v.re * tmp.re + v.im * tmp.im;

	// bisector: v.re * x + v.im * y = tmp

	if (v.re) {
            p0 = new Complex( tmp         / v.re, 0);
            p1 = new Complex((tmp - v.im) / v.re, 1);
	}
	else {
            if (!v.im) return; // cp0 and cp1 are the same
            // (cp0-cp1) is a vertical line; bisector is horizontal
            p0 = new Complex(0, tmp / v.im);
            p1 = new Complex(1, tmp / v.im);
	}

	// make sure that p0 is in the left side of vector cp0->cp1
	mul(sub(cp1, cp0), conj(sub(p0, cp0))).im >= 0 && // in right
            (tmp = p0, p0 = p1, p1 = tmp); // swap

	// origami_fold
	// tmp: new_state
	tmp = fold(cur_state.concat().reverse(), [], function(zz, facet) {
            // cut a given facet by a line p0-p1 (if they have any intersection)
            // find all cross points of a line (p0-p1) and any edges
            var z = fold2(facet.points, [[], []], function(z, p2, p3) {
		var z0 = push(z[0], p2),
		va = sub(p1, p0),
		tmp = div(sub(p3.dst, p2.dst), va);
		return tmp.im != 0 && (tmp = div(sub(p2.dst, p0), va).im / -tmp.im, 0 <= tmp && tmp < 1) ? (
                        // tmp: dst_cp
                        tmp = add(p2.dst, mul(sub(p3.dst, p2.dst), new Complex(tmp, 0))),
                        // tmp: new_point
                        tmp = new Point(add(mul(sub(p3.src, p2.src), div(sub(tmp, p2.dst), sub(p3.dst, p2.dst))), p2.src), tmp),
                        [push(z[1], tmp), push(z0, tmp)]
                ):
                    [z0, z[1]];
            });

            z = z[1].length ? (
                    // check if nfacet0 is in left
                    mul(sub(p1, p0), conj(sub(z[0][0].dst, p0))).im >= 0 && // in right
                    (z = z.reverse()),
                    // cut!
                    map(z, function(points) {
                        return new Facet(facet.front,
                                // normalize
                                fold2(points, [], function(z, p0, p1) {
                                    return p0.dst.re == p1.dst.re &&
                                        p0.dst.im == p1.dst.im &&
                                        p0.src.re == p1.src.re &&
                                        p0.src.im == p1.src.im ? z : push(z, p0);
                                })
                                );
                    })
                    ):
		mul(sub(p1, p0), conj(sub(facet.points[0].dst, p0))).im >= 0 ? // in right
                    [0, facet]
		:
                    [facet];
                z[0] && zz.unshift(z[0]);
                if (z[1]) {
		// flip_facet
		var v1 = sub(p1, p0);
		v1 = div(v1, conj(v1));
		zz = push(zz, new Facet(!z[1].front, 
                    map(z[1].points, function(p) {
                        return new Point(p.src, add(mul(conj(sub(p.dst, p0)), v1), p0));
                    })));
            }
            return zz;
	});
	if (preview) {
            redraw(tmp);
            var ctx = $(literal("#dst"))[0].getContext("2d");
            // draw_point
            each([cp0, cp1], function(cp) {
		ctx.fillStyle = literal("#000000");
		ctx.fillRect(cp.re - 1/128, cp.im - 1/128, 1/64, 1/64);
            });
	}
	else
            state_stack.push(cur_state),
            cur_state = tmp,
            flipped = 0,
            redraw(cur_state);
    }
}

function load_images(files) {
    if (files.length == 0)
	// main
	$(literal("#flip")).click(function() {
            cur_state = flipped ?
		state_stack.pop()
            :
		(
                    state_stack.push(cur_state),
                    map(cur_state, function(facet) {
			return new Facet(!facet.front, map(facet.points, function(p) {
                            return new Point(p.src, flip_c(p.dst));
			}));
                    }).reverse()
		);
            flipped = !flipped;
            redraw(cur_state);
	}),
	$(literal("#undo")).click(function() {
            if (state_stack.length >= 1) cur_state = state_stack.pop();
            redraw(cur_state);
	}),
	literal($.map)(literal(problems), function(v, k) {
            literal($("#origami #silhouette-list").append)(literal('<li data-silhouette-id="')+k+literal('"><a href="#">')+k+literal('</a></li>'));
	}),
	each([0,1], function(i) {
            var s = literal("#origami #") + (i ? literal("silhouette") : literal("texture")),
		dom = $(i ? literal("#dst") : literal("#src")),
		screen_height = dom.height() / 2 + 128,
		margin_width = dom.width() / 2 - 128,
		start_point = 0;
            $(s + literal(" a")).click(function(e) {
		e.preventDefault();
		e = literal("active");
		$(s + literal(" li")).removeClass(e);
		$(this).parent().addClass(e);
		redraw(cur_state);
            });

            if (i) {
		var tr = function(m) {
		    var x = m.offsetX, y = m.offsetY;
		    var z = m.originalEvent.changedTouches;
		    if (z) {
			var d = literal($("#dst"))[0].getBoundingClientRect();
			x = z[0].pageX - d.left;
			y = z[0].pageY - d.top;
		    }
                    return new Complex(
			(x - margin_width) / 256,
			(screen_height - y) / 256
                    );
		},f;
		dom.mousedown(f = function(e) {
                    $(literal("#navi")).remove();
                    start_point = tr(e);
                    return false;
		});
		dom.bind(literal("touchstart"),f);
		dom.mousemove(f = function(e) {
                    next_state(start_point, tr(e), 1);
                    return false;
		});
		dom.bind(literal("touchmove"),f);
		dom.mouseup(f = function(e) {
                    next_state(start_point, tr(e));
                    start_point = 0;
                    return false;
		});
		dom.bind(literal("touchend"),f);
            }
            dom[0].getContext("2d").setTransform(256, 0, 0, -256, margin_width, screen_height);
	}),
	redraw(cur_state);
    else {
	var img = new Image();
	imgs.push(img);
	img.onload = function() { load_images(files); };
	img.src = literal("texture") + files.shift() + literal(".png");
    }
}

$(function() {
    load_images(literal([0,1,2,3]));
});
