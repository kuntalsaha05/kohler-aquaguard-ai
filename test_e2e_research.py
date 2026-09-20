"""End-to-End Test for Research-Grade Enhancements in KOHLER AquaGuard AI."""
from fastapi.testclient import TestClient
from app.main import app, STORE
from app import sim, engine

def run_tests():
    with TestClient(app) as client:
        print("Testing /api/state...")
        r = client.get('/api/state')
        assert r.status_code == 200, f'status {r.status_code}'
        state = r.json()
        assert 'facility_health' in state, 'facility_health missing'
        assert 'heatmap' in state, 'heatmap missing'
        assert 'incidents' in state, 'incidents missing'
        print('  [PASS] composite health =', state['facility_health']['composite_score'])
        print('  [PASS] Heatmap terminals:', [t['terminal'] for t in state['heatmap']])

        print("\nTesting /api/facility-health...")
        r = client.get('/api/facility-health')
        assert r.status_code == 200
        fh = r.json()
        assert 'sub_indices' in fh
        print('  [PASS] Sub-indices count:', len(fh['sub_indices']))

        print("\nTesting /api/heatmap...")
        r = client.get('/api/heatmap')
        assert r.status_code == 200
        assert len(r.json()['heatmap']) == 4
        print('  [PASS] Heatmap 4 terminals confirmed')

        print("\nTesting /api/evaluation...")
        r = client.get('/api/evaluation')
        assert r.status_code == 200
        ev = r.json()
        assert 'detectors' in ev
        print('  [PASS] Benchmark version:', ev['evaluation_version'])

        print("\nTesting continuous-leak simulation & detection...")
        r = client.post('/simulate/continuous-leak')
        assert r.status_code == 200
        leak_data = r.json()
        dev_id = leak_data['device_id']
        print(f'  Injected continuous-leak on {dev_id}')

        for _ in range(6):
            events = sim.generate_tick(STORE)
            engine.process_events(STORE, events)

        alerts_res = client.get('/alerts?status=OPEN').json()
        open_alerts = alerts_res['alerts']
        leak_alert = next((a for a in open_alerts if a['device_id'] == dev_id), None)
        assert leak_alert is not None, 'Leak alert not found'
        print('  [PASS] Leak alert confirmed:', leak_alert['id'])
        print('         Leak confidence:', leak_alert.get('leak_confidence'))
        print('         Root cause:', leak_alert.get('root_cause'))
        print('         SLA min:', leak_alert.get('sla_minutes'), 'rem sec:', leak_alert.get('sla_remaining_seconds'))
        print('         Before state:', leak_alert.get('before_state'))

        print("\nTesting canonical IncidentIntelligence...")
        inc_res = client.get('/api/incidents').json()
        incidents = inc_res['incidents']
        matching_inc = next((i for i in incidents if i['device_id'] == dev_id), None)
        assert matching_inc is not None, 'Matching IncidentIntelligence not found'
        print('  [PASS] Incident ID:', matching_inc['incident_id'])

        print("\nTesting alert resolution and before-vs-after verification...")
        aid = leak_alert['id']
        res_alert = client.post(f'/alerts/{aid}/resolve').json()
        print('  [PASS] Alert resolved. Monthly liters saved:', res_alert['saved_month_liters'])

        resolved_alert = next(a for a in STORE.alerts if a.id == aid)
        assert resolved_alert.after_state is not None
        print('  [PASS] After state verified:', resolved_alert.after_state)

        print("\nTesting AI Command Center Grounded ReAct...")
        q1 = client.post('/ai', json={'query': 'Show research benchmarks'}).json()
        assert any(t['tool'] == 'get_model_evaluation_metrics' for t in q1['tool_trail'])
        print('  [PASS] Benchmark query:', [t['tool'] for t in q1['tool_trail']])

        q2 = client.post('/ai', json={'query': 'Explain facility health hierarchy'}).json()
        assert any(t['tool'] == 'get_facility_health_hierarchy' for t in q2['tool_trail'])
        print('  [PASS] Health hierarchy query:', [t['tool'] for t in q2['tool_trail']])

        q3 = client.post('/ai', json={'query': 'Show water waste heatmap'}).json()
        assert any(t['tool'] == 'get_water_waste_heatmap' for t in q3['tool_trail'])
        print('  [PASS] Heatmap query:', [t['tool'] for t in q3['tool_trail']])

        q4 = client.post('/ai', json={'query': f'Why {dev_id}'}).json()
        assert any(t['tool'] == 'get_sensor_fusion_breakdown' for t in q4['tool_trail'])
        print('  [PASS] Device sensor fusion query:', [t['tool'] for t in q4['tool_trail']])

        client.post('/simulate/stop')
        print('\n======================================')
        print('ALL RESEARCH PLATFORM TESTS PASSED!')
        print('======================================')

if __name__ == '__main__':
    run_tests()
