
import os, json
os.environ['BENCHMESH_START_UI']='0'
from benchmesh_service.api import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
    lst = c.get('/instruments').json()
    print('devices:', [d['id'] for d in lst])
    # Try for device with driver owon_spm or tenma_psu
    target = None
    for dev in lst:
        if dev['id'] == 'psu-1' or dev.get('IDN','').find('SPM')>=0:
            target = dev['id']
            break
    target = target or (lst[0]['id'] if lst else None)
    print('target:', target)
    for klass in ['PSU','DMM']:
        r = c.get(f'/instruments/{klass}/{target}')
        print('GET', klass, '->', r.status_code)
        if r.status_code==200:
            print('features keys:', list(r.json().keys())[:10])
