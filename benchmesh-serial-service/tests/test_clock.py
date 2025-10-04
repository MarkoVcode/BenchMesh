from benchmesh_service.clock import Clock, ManualClock

def test_clock_now_advances():
    c = ManualClock(10.0)
    assert c.now() == 10.0
    c.advance(0.5)
    assert c.now() == 10.5
