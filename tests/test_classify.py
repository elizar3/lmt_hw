# AI

from app.logic.classify import classify_threat, ThreatLevel

def test_not_threat_low_speed():
    assert classify_threat(10, 1000) == ThreatLevel.NOT_THREAT

def test_not_threat_low_altitude():
    assert classify_threat(100, 100) == ThreatLevel.NOT_THREAT

def test_threat():
    assert classify_threat(51, 500) == ThreatLevel.THREAT

def test_caution():
    assert classify_threat(20, 500) == ThreatLevel.CAUTION

def test_potential_threat():
    assert classify_threat(15, 500) == ThreatLevel.POTENTIAL_THREAT
