
import os
os.environ["BENCHMESH_START_UI"] = "0"
from benchmesh_service.api import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
    r = c.get("/instruments")
    print("GET /instruments ->", r.status_code)
    data = r.json()
    print("instruments count:", len(data))
    if data:
        dev_id = data[0]['id']
        for klass in ["PSU","DMM","OSC","GEN","LCR"]:
            resp = c.get(f"/instruments/{klass}/{dev_id}")
            print(klass, '->', resp.status_code)
            if resp.status_code == 200:
                print('features keys:', list(resp.json().keys())[:5])
                break
