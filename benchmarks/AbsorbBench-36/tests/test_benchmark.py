"""Synthetic tests only. No study observations or successful design examples."""
import copy
import csv
import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import absorbbench as ab
import geometry


class MetricTests(unittest.TestCase):
    def test_all_below_threshold(self):
        self.assertEqual(ab.coverage_one([2,3,4],[0.05]*3,[2,4],-10)['coverage'],1)

    def test_inclusive_threshold(self):
        self.assertEqual(ab.coverage_one([2,4],[0.1]*2,[2,4],-10)['coverage'],1)

    def test_both_endpoints_required(self):
        self.assertEqual(ab.coverage_one([2,3,4],[0.01,0.2,0.01],[2,4],-10)['coverage'],0)

    def test_bandwidth_not_sample_fraction(self):
        self.assertEqual(ab.coverage_one([2,3,5],[0.01,0.01,0.2],[2,5],-10)['coverage'],1/3)

    def test_longest_separate_segments(self):
        r=ab.coverage_one([2,3,4,5,6,7],[0.01,0.01,0.2,0.01,0.01,0.01],[2,7],-10)
        self.assertEqual(r['coverage'],3/5)
        self.assertEqual(r['longest_contiguous_band_GHz'],2)

    def test_bad_spectra_rejected(self):
        for f,r in [([2,4],[0.1]),([2,2],[0.1,0.1]),([2,4],[float('nan'),0.1]),([2,4],[-0.1,0.1])]:
            with self.subTest(f=f,r=r), self.assertRaises(ValueError):
                ab.coverage_one(f,r,[2,4],-10)

    def test_missing_band_endpoint(self):
        with self.assertRaises(ValueError):
            ab.coverage_one([2,3,4],[0.01]*3,[2.5,4],-10)


class TaskTests(unittest.TestCase):
    def test_pack_and_hashes(self):
        self.assertEqual(ab.validate_pack()['tasks'],36)

    def test_all_initials_and_geometry(self):
        for p in (ROOT/'tasks').glob('*.json'):
            t=ab.read_json(p)
            self.assertFalse(ab.parameters_errors(t,t['initial_design']['parameters']))
            self.assertTrue(geometry.resolve(t,t['initial_design']['parameters']))

    def test_illegal_parameter_types_and_bounds(self):
        t=ab.read_json(ab.task_path('AB36-HC-D01'))
        for v in (True,float('inf'),-1,500):
            p=copy.deepcopy(t['initial_design']['parameters']); p['core_height_mm']=v
            self.assertTrue(ab.parameters_errors(t,p))

    def test_no_extra_fixed_parameter(self):
        t=ab.read_json(ab.task_path('AB36-HC-D01')); p=dict(t['initial_design']['parameters'],cell_width_mm=99)
        self.assertTrue(ab.parameters_errors(t,p))

    def test_tpms_discrete_grid_and_topology(self):
        t=ab.read_json(ab.task_path('AB36-TPMS-T07')); p=copy.deepcopy(t['initial_design']['parameters'])
        p['target_vf']=0.295; self.assertTrue(ab.parameters_errors(t,p))
        p['target_vf']=0.29; p['topology']='Primitive'; self.assertTrue(ab.parameters_errors(t,p))

    def test_legacy_level_preserved(self):
        t=ab.read_json(ab.task_path('AB36-TPMS-D01'))
        self.assertIn('level_half_width',t['design_space']['variables'])
        self.assertNotIn('target_vf',t['design_space']['variables'])

    def test_frozen_vf_mapping(self):
        t=ab.read_json(ab.task_path('AB36-TPMS-T07'))
        g=geometry.resolve(t,t['initial_design']['parameters'])
        self.assertAlmostEqual(g['level_half_width'],0.3473986670830173)

    def test_honeycomb_period_and_closed_profiles(self):
        g=geometry.honeycomb_profiles(2.55,0.055,60,0.1,10)
        self.assertAlmostEqual(g['xy_periods'][0],2*(2.55*1.5+0.055/math.sqrt(3)))
        self.assertEqual(len(g['profiles_xy']['Nomex']),22)
        self.assertEqual(len(g['profiles_xy']['coating_1']),8)
        self.assertEqual(len(g['profiles_xy']['coating_3']),10)
        self.assertEqual(g['z_core'],[1.2,11.2])


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.tid='AB36-HC-D01'; self.data=ab.template(self.tid)
        self.data['round_index']=1
        for a in self.data['angle_results']:
            a['checks']={k:True for k in ab.CHECKS}
            (self.root/a['solver_log']).write_text('SYNTHETIC TEST FIXTURE; NOT A PHYSICAL SOLVE',encoding='utf-8')
        self.spectrum(0.05,0.05)

    def tearDown(self):
        self.tmp.cleanup()

    def spectrum(self,te,tm):
        t=ab.read_json(ab.task_path(self.data['task_id'])); n=t['simulation']['frequency_samples']
        for a in self.data['angle_results']:
            with (self.root/a['spectrum_csv']).open('w',encoding='utf-8',newline='') as f:
                w=csv.writer(f); w.writerow(ab.COLUMNS)
                for i in range(n): w.writerow([2+16*i/(n-1),math.sqrt(te),0,0,0,math.sqrt(tm),0,0,0])

    def evaluate(self):
        p=self.root/'evaluation.json'; p.write_text(json.dumps(self.data),encoding='utf-8'); return ab.score(p)

    def test_complete_synthetic_input(self):
        r=self.evaluate(); self.assertTrue(r['goal_success']); self.assertEqual(r['coverage'],1)

    def test_equal_mean_selected_polarizations(self):
        self.spectrum(0.05,0.2)
        r=self.evaluate(); self.assertEqual(r['coverage'],0.5); self.assertFalse(r['goal_success'])

    def test_cross_polarization_counts(self):
        a=self.data['angle_results'][0]; path=self.root/a['spectrum_csv']
        with path.open() as f: rows=list(csv.DictReader(f))
        for r in rows: r['R_TE_cross_real']='0.8'; r['R_TM_cross_real']='0.8'
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=ab.COLUMNS); w.writeheader(); w.writerows(rows)
        self.assertEqual(self.evaluate()['coverage'],0)

    def test_power_overflow_unresolved(self):
        self.spectrum(1.01,0.05); r=self.evaluate()
        self.assertIsNone(r['goal_success']); self.assertIsNone(r['coverage']); self.assertFalse(r['scientifically_terminal'])

    def test_unverified_template_rejected(self):
        self.data['angle_results'][0]['checks']['solver_converged']=False
        with self.assertRaises(ValueError): self.evaluate()

    def test_task_mutation_rejected(self):
        self.data['task_sha256']='0'*64
        with self.assertRaises(ValueError): self.evaluate()

    def test_missing_mode_rejected(self):
        path=self.root/self.data['angle_results'][0]['spectrum_csv']
        path.write_text('frequency_GHz,R_TE_co_real\n2,0.2\n18,0.2\n')
        with self.assertRaises(ValueError): self.evaluate()

    def test_missing_log_rejected(self):
        (self.root/self.data['angle_results'][0]['solver_log']).unlink()
        with self.assertRaises(ValueError): self.evaluate()

    def test_angle_mismatch_rejected(self):
        self.data['angle_results'][0]['angle_deg']=30
        with self.assertRaises(ValueError): self.evaluate()

    def test_infrastructure_failure_is_not_failure_score(self):
        self.data.update(status='infrastructure_failure',reason='Synthetic infrastructure failure')
        r=self.evaluate(); self.assertIsNone(r['goal_success']); self.assertFalse(r['scientifically_terminal'])

    def test_invalid_proposal_consumes_round(self):
        self.data.update(status='invalid_proposal',reason='Synthetic out-of-domain proposal')
        r=self.evaluate(); self.assertIs(r['goal_success'],False); self.assertTrue(r['scientifically_terminal'])

    def test_no_sixth_round(self):
        self.data['round_index']=6
        with self.assertRaises(ValueError): self.evaluate()

    def test_initial_cannot_be_changed(self):
        self.data['round_index']=0; self.data['parameters']['core_height_mm']=10
        with self.assertRaises(ValueError): self.evaluate()

    def test_partial_summary_keeps_rate_null_and_detects_duplicates(self):
        r=self.evaluate(); path=self.root/'score.json'; path.write_text(json.dumps(r),encoding='utf-8')
        s=ab.summarize([path],'development')
        self.assertFalse(s['complete']); self.assertIsNone(s['task_success_rate'])
        self.assertEqual(s['observed_successful_tasks'],1)
        self.assertIsNone(s['mean_best_coverage_including_initial'])
        with self.assertRaises(ValueError): ab.summarize([path,path],'development')


if __name__=='__main__':
    unittest.main()
