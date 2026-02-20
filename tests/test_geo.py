# AI

import math
import pytest

from app.logic.geo import haversine_distance_m


def test_zero_distance_same_point():
    assert haversine_distance_m(56.97475845607155, 24.1670070219384,
                                56.97475845607155, 24.1670070219384) == 0.0


def test_symmetry_distance_is_same_both_directions():
    a = (56.97475845607155, 24.1670070219384)      # Riga base
    b = (56.516083346891044, 21.0182217849017)     # Liepaja base

    d1 = haversine_distance_m(a[0], a[1], b[0], b[1])
    d2 = haversine_distance_m(b[0], b[1], a[0], a[1])

    assert math.isclose(d1, d2, rel_tol=1e-12, abs_tol=1e-9)


def test_one_degree_latitude_is_about_111_km():
    # Distance between (0,0) and (1,0) is ~111.195 km with Earth radius 6,371,000 m
    d = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert math.isclose(d, 111_195, rel_tol=0.01)  # 1% tolerance


def test_small_known_distance_approximately_1km():
    # Roughly ~1 km north (latitude + ~0.009 degrees at equator-ish)
    d = haversine_distance_m(0.0, 0.0, 0.009, 0.0)
    assert 900 <= d <= 1100


@pytest.mark.parametrize(
    "lat1,lon1,lat2,lon2",
    [
        (56.97475845607155, 24.1670070219384, 56.516083346891044, 21.0182217849017),  # Riga -> Liepaja
        (56.97475845607155, 24.1670070219384, 55.87409588616014, 26.51864225209475),  # Riga -> Daugavpils
        (56.516083346891044, 21.0182217849017, 55.87409588616014, 26.51864225209475), # Liepaja -> Daugavpils
    ],
)
def test_distance_is_positive_for_distinct_points(lat1, lon1, lat2, lon2):
    assert haversine_distance_m(lat1, lon1, lat2, lon2) > 0


def test_triangle_inequality_holds_approximately_for_latvia_bases():
    # Great-circle distances should satisfy triangle inequality (within floating error)
    riga = (56.97475845607155, 24.1670070219384)
    liepaja = (56.516083346891044, 21.0182217849017)
    daugavpils = (55.87409588616014, 26.51864225209475)

    d_rl = haversine_distance_m(*riga, *liepaja)
    d_rd = haversine_distance_m(*riga, *daugavpils)
    d_ld = haversine_distance_m(*liepaja, *daugavpils)

    # Check all three permutations with a small tolerance
    eps = 1e-6
    assert d_rl <= d_rd + d_ld + eps
    assert d_rd <= d_rl + d_ld + eps
    assert d_ld <= d_rl + d_rd + eps
