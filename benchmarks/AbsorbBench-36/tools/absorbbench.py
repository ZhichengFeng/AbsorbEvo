#!/usr/bin/env python3
"""Solver-independent AbsorbBench-36 task validation and spectrum scoring.

Python 3.10+, standard library only. No solver or model is called.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ('solver_converged', 'export_complete', 'contract_unchanged', 'fresh_project')
COLUMNS = ['frequency_GHz'] + [f'R_{p}_{c}_{z}' for p in ('TE','TM') for c in ('co','cross') for z in ('real','imag')]


def read_json(path):
    def reject(value):
        raise ValueError(f'Nonfinite JSON value: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def task_path(task_id):
    if task_id not in {p.stem for p in (ROOT/'tasks').glob('*.json')}:
        raise ValueError(f'Unknown task: {task_id}')
    return ROOT/'tasks'/f'{task_id}.json'


def parameters_errors(task, parameters):
    variables = task['design_space']['variables']
    if not isinstance(parameters, dict) or set(parameters) != set(variables):
        return [f'Expected exactly these active parameters: {sorted(variables)}']
    errors = []
    for name, spec in variables.items():
        value = parameters[name]
        if spec['type'] == 'number':
            if not finite_number(value) or not spec['minimum'] <= value <= spec['maximum']:
                errors.append(f'{name}: must be finite and within [{spec["minimum"]}, {spec["maximum"]}]')
            elif 'step' in spec and abs(value/spec['step']-round(value/spec['step'])) > 1e-8:
                errors.append(f'{name}: must lie on the {spec["step"]} grid')
        elif value not in spec['enum']:
            errors.append(f'{name}: must be one of {spec["enum"]}')
    return errors


def validate_pack():
    tasks = [read_json(p) for p in sorted((ROOT/'tasks').glob('*.json'))]
    assert len(tasks) == 36
    assert len({t['task_id'] for t in tasks}) == 36
    assert Counter(t['family'] for t in tasks) == {'Honeycomb':18, 'TPMS':18}
    assert Counter(t['split'] for t in tasks) == {'development':8, 'validation':4, 'test':24}
    split_ids = read_json(ROOT/'splits.json')
    for t in tasks:
        assert t['task_id'].startswith('AB36-')
        assert t['task_id'] in split_ids[t['split']]
        assert not parameters_errors(t, t['initial_design']['parameters']), t['task_id']
        o = t['objective']
        assert 0 < o['required_coverage'] <= 1
        assert o['frequency_band_GHz'][0] < o['frequency_band_GHz'][1]
        assert t['proposal_budget'] == 5
        assert o['polarizations'] in (['TE'], ['TM'], ['TE','TM'])
    for split, ids in split_ids.items():
        assert sorted(ids) == sorted(t['task_id'] for t in tasks if t['split']==split)
    manifest = read_json(ROOT/'checksums.json')
    for name, expected in manifest['sha256'].items():
        path = ROOT/name
        assert path.is_file() and digest(path) == expected, f'Checksum mismatch: {name}'
    return {'valid':True, 'tasks':36, 'splits':dict(Counter(t['split'] for t in tasks)),
            'initial_parameters_valid':36, 'checksums_verified':len(manifest['sha256'])}


def coverage_one(frequency, reflected_power, band, threshold_db):
    """Frozen conservative endpoint rule; no interpolation at threshold crossings."""
    if len(frequency) != len(reflected_power) or len(frequency)<2:
        raise ValueError('Spectrum lengths differ or are too short')
    if any(not finite_number(x) for x in [*frequency,*reflected_power]):
        raise ValueError('Nonfinite spectrum')
    if any(b <= a for a,b in zip(frequency,frequency[1:])):
        raise ValueError('Frequency must be strictly increasing')
    if any(x < 0 for x in reflected_power):
        raise ValueError('Negative reflected power')
    lo, hi = band
    rows = [(f,r) for f,r in zip(frequency,reflected_power) if lo-1e-10 <= f <= hi+1e-10]
    if len(rows)<2 or abs(rows[0][0]-lo)>1e-8 or abs(rows[-1][0]-hi)>1e-8:
        raise ValueError('Exact target-band endpoints are required')
    limit = 10**(threshold_db/10)
    qualified = longest = current = 0.0
    for (f0,r0),(f1,r1) in zip(rows,rows[1:]):
        if r0<=limit and r1<=limit:
            qualified += f1-f0
            current += f1-f0
            longest = max(longest,current)
        else:
            current = 0.0
    return {'coverage':qualified/(hi-lo), 'qualified_bandwidth_GHz':qualified,
            'longest_contiguous_band_GHz':longest}


def read_spectrum(path, task):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not set(COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError(f'Missing raw complex reflection columns in {path}')
        rows = [{k:float(r[k]) for k in COLUMNS} for r in reader]
    if any(not math.isfinite(v) for r in rows for v in r.values()):
        raise ValueError('Raw reflection data contain nonfinite values')
    n = task['simulation']['frequency_samples']
    freq = [r['frequency_GHz'] for r in rows]
    if len(rows)!=n or any(abs(f-(2+16*i/(n-1)))>1e-7 for i,f in enumerate(freq)):
        raise ValueError(f'Expected {n} uniformly spaced samples over 2-18 GHz')
    power={p:[sum(r[f'R_{p}_{c}_{z}']**2 for c in ('co','cross') for z in ('real','imag')) for r in rows] for p in ('TE','TM')}
    return freq, power


def score(input_path):
    input_path=Path(input_path).resolve()
    data=read_json(input_path)
    task=read_json(task_path(data['task_id']))
    if data.get('task_sha256') != digest(task_path(data['task_id'])):
        raise ValueError('Task hash mismatch; use the current immutable public task file')
    rnd=data.get('round_index')
    if type(rnd) is not int or rnd not in range(0,6):
        raise ValueError('round_index must be 0 (Initial) or 1-5 (new proposals)')
    result={'task_id':task['task_id'], 'task_sha256':data['task_sha256'], 'split':task['split'],
            'round_index':rnd, 'input_sha256':digest(input_path), 'coverage':None,
            'goal_success':None, 'scientifically_terminal':False,
            'verification_scope':'spectrum checks plus external runner attestations; not independent solver certification'}
    status=data.get('status')
    if status in ('invalid_proposal','infrastructure_failure'):
        if not isinstance(data.get('reason'),str) or not data['reason'].strip():
            raise ValueError('A nonempty reason is required for an unsuccessful attempt')
        if rnd==0:
            raise ValueError('Initial calibration must be a completed evaluation')
        result.update(status=status, reason=data['reason'])
        if status=='invalid_proposal':
            result.update(goal_success=False, scientifically_terminal=True)
        return result
    if status != 'complete':
        raise ValueError('status must be complete, invalid_proposal or infrastructure_failure')
    errors=parameters_errors(task,data.get('parameters'))
    if errors:
        raise ValueError('; '.join(errors))
    if rnd==0 and data['parameters']!=task['initial_design']['parameters']:
        raise ValueError('Round 0 parameters must equal the supplied Initial')
    angles=data.get('angle_results',[])
    if not isinstance(angles,list) or len(angles)!=len(task['objective']['angles_deg']):
        raise ValueError('Exactly one completed result per required angle is necessary')
    provided=[a.get('angle_deg') for a in angles]
    if any(not finite_number(v) for v in provided) or sorted(provided)!=sorted(task['objective']['angles_deg']):
        raise ValueError('Missing, duplicate or unexpected incidence angles')
    angle_scores=[]
    for angle in angles:
        if any(angle.get('checks',{}).get(k) is not True for k in CHECKS):
            raise ValueError('Solver convergence, export, fixed contract and fresh project attestations must all be true')
        log=input_path.parent/angle['solver_log']
        if not log.is_file() or log.stat().st_size==0:
            raise ValueError('A nonempty solver log file is required for each angle')
        spectrum=input_path.parent/angle['spectrum_csv']
        freq,power=read_spectrum(spectrum,task)
        if any(r>1.005 for p in power.values() for r in p):
            result.update(status='invalid_evidence', reason='Two-mode reflected power exceeds 1.005')
            return result
        per_pol={p:coverage_one(freq,power[p],task['objective']['frequency_band_GHz'],task['objective']['reflection_loss_threshold_dB']) for p in ('TE','TM')}
        selected=task['objective']['polarizations']
        angle_scores.append({'angle_deg':angle['angle_deg'], 'per_polarization':per_pol,
                             'coverage':sum(per_pol[p]['coverage'] for p in selected)/len(selected),
                             'spectrum_sha256':digest(spectrum),'solver_log_sha256':digest(log)})
    coverage=sum(a['coverage'] for a in angle_scores)/len(angle_scores)
    result.update(status='complete', coverage=coverage, goal_success=coverage>=task['objective']['required_coverage'],
                  scientifically_terminal=True, angle_scores=angle_scores,
                  parameters=data['parameters'])
    return result


def summarize(paths, split):
    ids=read_json(ROOT/'splits.json')[split]
    records={}
    for path in paths:
        r=read_json(path)
        if r.get('task_id') not in ids:
            raise ValueError(f'Record from outside {split}: {path}')
        if r.get('task_sha256') != digest(task_path(r['task_id'])):
            raise ValueError(f'Wrong task version: {path}')
        rnd=r.get('round_index')
        if type(rnd) is not int or rnd not in range(6):
            raise ValueError(f'Invalid round: {path}')
        key=(r['task_id'],rnd)
        if key in records:
            raise ValueError(f'Duplicate record {key}; retries must not become new opportunities')
        # Accept only scorer-shaped receipts; never impute missing outcomes.
        if r.get('status')=='complete':
            if not finite_number(r.get('coverage')) or not 0<=r['coverage']<=1+1e-10:
                raise ValueError(f'Invalid coverage: {path}')
            expected=r['coverage']>=read_json(task_path(r['task_id']))['objective']['required_coverage']
            if r.get('goal_success') is not expected or r.get('scientifically_terminal') is not True:
                raise ValueError(f'Inconsistent completed record: {path}')
        elif r.get('status')=='invalid_proposal':
            if r.get('goal_success') is not False or r.get('coverage') is not None or r.get('scientifically_terminal') is not True:
                raise ValueError(f'Inconsistent invalid proposal: {path}')
        elif r.get('status') in ('infrastructure_failure','invalid_evidence'):
            if r.get('goal_success') is not None or r.get('coverage') is not None or r.get('scientifically_terminal') is not False:
                raise ValueError(f'Inconsistent unresolved record: {path}')
        else:
            raise ValueError(f'Unknown result status: {path}')
        records[key]=r
    details=[]
    for tid in ids:
        rounds=[records.get((tid,k)) for k in range(1,6)]
        success=[k for k,r in enumerate(rounds,1) if r and r.get('goal_success') is True]
        missing=[k for k,r in enumerate(rounds,1) if not r or not r.get('scientifically_terminal')]
        init=records.get((tid,0))
        valid=[r['coverage'] for r in rounds if r and r.get('status')=='complete']
        if init and init.get('status')=='complete':
            valid.append(init['coverage'])
        details.append({'task_id':tid, 'first_success_round':min(success) if success else None,
                        'complete':not missing,'unresolved_rounds':missing,
                        'best_coverage_including_initial':max(valid) if valid and init and init.get('status')=='complete' else None})
    complete=all(d['complete'] for d in details)
    count=sum(d['first_success_round'] is not None for d in details)
    return {'split':split,'expected_tasks':len(ids),'expected_opportunities':5*len(ids),
            'scientifically_terminal_opportunities':sum(bool(r.get('scientifically_terminal')) for (tid,k),r in records.items() if k>0),
            'complete':complete,'observed_successful_tasks':count,
            'task_success_rate':count/len(ids) if complete else None,
            'cumulative_successful_tasks':{str(k):sum(d['first_success_round'] is not None and d['first_success_round']<=k for d in details) for k in range(1,6)},
            'mean_best_coverage_including_initial':sum(d['best_coverage_including_initial'] for d in details)/len(details) if complete and all(d['best_coverage_including_initial'] is not None for d in details) else None,
            'tasks':details}


def template(task_id):
    task=read_json(task_path(task_id))
    return {'task_id':task_id,'task_sha256':digest(task_path(task_id)), 'round_index':0,
            'status':'complete','parameters':task['initial_design']['parameters'],
            'angle_results':[{'angle_deg':a,'spectrum_csv':f'theta_{a:g}.csv','solver_log':f'theta_{a:g}.log',
                              'checks':{k:False for k in CHECKS}} for a in task['objective']['angles_deg']]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('validate')
    for name in ('show','template'):
        q=sub.add_parser(name); q.add_argument('task_id')
        if name=='template': q.add_argument('--out')
    q=sub.add_parser('check-proposal'); q.add_argument('task_id'); q.add_argument('parameters_json')
    q=sub.add_parser('score'); q.add_argument('evaluation_json'); q.add_argument('--out',required=True)
    q=sub.add_parser('summarize'); q.add_argument('score_files',nargs='+'); q.add_argument('--split',choices=['development','validation','test'],default='test'); q.add_argument('--out',required=True)
    a=p.parse_args()
    try:
        if a.command=='validate': value=validate_pack()
        elif a.command=='show': value=read_json(task_path(a.task_id))
        elif a.command=='template': value=template(a.task_id)
        elif a.command=='check-proposal':
            errors=parameters_errors(read_json(task_path(a.task_id)),read_json(a.parameters_json))
            if errors: raise ValueError('; '.join(errors))
            value={'valid':True,'task_id':a.task_id}
        elif a.command=='score': value=score(a.evaluation_json)
        else: value=summarize(a.score_files,a.split)
        text=json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if getattr(a,'out',None):
            Path(a.out).write_text(text,encoding='utf-8')
        else: print(text,end='')
    except (ValueError,KeyError,TypeError,AssertionError,OSError) as exc:
        p.exit(2,f'Error: {exc}\n')


if __name__=='__main__':
    main()
