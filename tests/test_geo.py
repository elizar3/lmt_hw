# AI

import math

from app.logic.geo import (
    EARTH_RADIUS_M,
    haversine_distance_m,
    latlon_to_local_xy_m,
    destination_point,
)


def test_haversine_zero_distance_same_point():
    d = haversine_distance_m(56.97475845607155, 24.1670070219384,
                             56.97475845607155, 24.1670070219384)
    assert d == 0.0


def test_haversine_is_symmetric():
    riga = (56.97475845607155, 24.1670070219384)
    liepaja = (56.516083346891044, 21.0182217849017)

    d1 = haversine_distance_m(*riga, *liepaja)
    d2 = haversine_distance_m(*liepaja, *riga)

    assert math.isclose(d1, d2, rel_tol=1e-12, abs_tol=1e-9)


def test_haversine_one_degree_latitude_about_111km():
    # With EARTH_RADIUS_M = 6,371,000 m this is about 111,194.9 m
    d = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert math.isclose(d, 111_195, rel_tol=0.01)


def test_latlon_to_local_xy_zero_at_origin():
    x, y = latlon_to_local_xy_m(56.97, 24.16, 56.97, 24.16)
    assert x == 0.0
    assert y == 0.0


def test_latlon_to_local_xy_signs_east_and_north():
    # At equator, 0.001 deg longitude ~= 111.2 m east
    x_east, y_east = latlon_to_local_xy_m(0.0, 0.0, 0.0, 0.001)
    assert x_east > 0
    assert abs(y_east) < 1e-6
    assert math.isclose(x_east, 111.195, rel_tol=0.02)

    # 0.001 deg latitude ~= 111.2 m north
    x_north, y_north = latlon_to_local_xy_m(0.0, 0.0, 0.001, 0.0)
    assert y_north > 0
    assert abs(x_north) < 1e-6
    assert math.isclose(y_north, 111.195, rel_tol=0.02)


def test_destination_point_zero_distance_returns_same_point():
    lat, lon = 56.97475845607155, 24.1670070219384
    lat2, lon2 = destination_point(lat, lon, 90, 0)

    assert lat2 == lat
    assert lon2 == lon


def test_destination_point_north_1000m():
    lat0, lon0 = 0.0, 0.0
    lat1, lon1 = destination_point(lat0, lon0, 0, 1000)

    # Should move north and stay near same longitude
    assert lat1 > lat0
    assert abs(lon1 - lon0) < 1e-6

    d = haversine_distance_m(lat0, lon0, lat1, lon1)
    assert math.isclose(d, 1000, rel_tol=0.01)


def test_destination_point_east_1000m():
    lat0, lon0 = 0.0, 0.0
    lat1, lon1 = destination_point(lat0, lon0, 90, 1000)

    # Should move east and stay near same latitude (at equator)
    assert lon1 > lon0
    assert abs(lat1 - lat0) < 1e-6

    d = haversine_distance_m(lat0, lon0, lat1, lon1)
    assert math.isclose(d, 1000, rel_tol=0.01)


def test_destination_point_and_local_xy_are_consistent_for_small_distance():
    # Small local movement: east 1500 m
    lat0, lon0 = 56.0, 24.0
    lat1, lon1 = destination_point(lat0, lon0, 90, 1500)

    x, y = latlon_to_local_xy_m(lat0, lon0, lat1, lon1)

    assert x > 0
    assert abs(y) < 10  # small numerical approximation error is fine
    assert math.isclose(x, 1500, rel_tol=0.02)


def test_earth_radius_constant():
    assert EARTH_RADIUS_M == 6_371_000