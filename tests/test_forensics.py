import figforge as ff


def test_size_and_gradient_rect(sample_svg):
    doc = ff.parse_svg(sample_svg)
    assert (doc.width, doc.height) == (680, 362)
    band = next(
        r for r in doc.rects if (g := doc.gradient_for(r)) and g.kind == "linear"
    )
    assert (band.x, band.w, band.h) == (423, 177, 322)
    g = doc.gradient_for(band)
    assert g.vertical
    assert g.stops[0].color == "#EFBF04" and g.stops[0].opacity == 1.0
    assert g.stops[-1].opacity == 0.0


def test_group_filter_resolved_to_child_rect(sample_svg):
    doc = ff.parse_svg(sample_svg)
    band = next(r for r in doc.rects if doc.gradient_for(r))
    sh = doc.shadow_for(band)  # filter lives on the wrapping <g>
    assert sh is not None
    assert sh.opacity == 0.25 and sh.blur == 2.0 and sh.dy == 4.0


def test_pattern_crop_fractions(sample_svg):
    doc = ff.parse_svg(sample_svg)
    man = next(r for r in doc.rects if doc.pattern_for(r))
    pat = doc.pattern_for(man)
    assert pat.image_w == 1024 and pat.image_h == 1024
    x0, x1, y0, y1 = doc.pattern_crop(pat.id)
    assert abs(x0) < 1e-6 and 0.9 < x1 < 1.0  # right edge slightly cropped
    assert abs(y0) < 1e-6 and abs(y1 - 1.0) < 1e-3  # full height
