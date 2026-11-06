import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fetcher import _geometry_centroid, interleave_by_source


def test_unit_square_centroid():
    geo = {"type": "Polygon",
           "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    lat, lon = _geometry_centroid(geo)
    assert lat == pytest.approx(0.5)
    assert lon == pytest.approx(0.5)


def test_centroid_returns_lat_lon_order():
    # Square spanning lon -98..-96, lat 27..29 (near Corpus Christi, TX)
    geo = {"type": "Polygon",
           "coordinates": [[[-98, 27], [-96, 27], [-96, 29], [-98, 29], [-98, 27]]]}
    lat, lon = _geometry_centroid(geo)
    assert lat == pytest.approx(28.0)
    assert lon == pytest.approx(-97.0)


def test_multipolygon_uses_largest_part():
    small = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]        # area 1, centroid (0.5, 0.5)
    large = [[[10, 10], [14, 10], [14, 14], [10, 14], [10, 10]]]  # area 16, centroid (12, 12)
    geo = {"type": "MultiPolygon", "coordinates": [small, large]}
    lat, lon = _geometry_centroid(geo)
    assert lat == pytest.approx(12.0)
    assert lon == pytest.approx(12.0)


@pytest.mark.parametrize("geo", [None, {}, {"type": "Polygon", "coordinates": []}])
def test_missing_geometry_returns_none(geo):
    assert _geometry_centroid(geo) is None


def test_interleave_gives_each_source_a_share():
    usgs = [{"source": "USGS"}] * 10
    noaa = [{"source": "NOAA"}] * 8
    news = [{"source": "NewsAPI"}] * 5
    selected = interleave_by_source(usgs, noaa, news)[:8]
    assert len(selected) == 8
    sources = [e["source"] for e in selected]
    assert set(sources) == {"USGS", "NOAA", "NewsAPI"}
    assert max(sources.count(s) for s in set(sources)) < 8


def test_interleave_fills_slots_when_a_source_is_empty():
    usgs = [{"source": "USGS"}] * 10
    noaa = [{"source": "NOAA"}] * 8
    selected = interleave_by_source(usgs, noaa, [])[:8]
    assert len(selected) == 8
    assert [e["source"] for e in selected].count("NOAA") == 4
