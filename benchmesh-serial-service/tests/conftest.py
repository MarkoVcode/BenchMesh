import os, sys
import pytest

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

@pytest.fixture
def manual_clock():
    from benchmesh_service.clock import ManualClock
    return ManualClock(start=0.0)
