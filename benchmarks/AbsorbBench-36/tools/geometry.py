#!/usr/bin/env python3
"""Export solver-neutral geometry inputs; no electromagnetic calculations."""
import argparse
import csv
import json
import math
from pathlib import Path

from absorbbench import ROOT, parameters_errors, read_json, task_path


def honeycomb_profiles(s, t, angle, b, h):
    """Polygon profiles of the frozen coated rectangular honeycomb unit cell."""
    rad=math.radians(angle); sn,cs=math.sin(rad),math.cos(rad); ct=cs/sn
    a=(s/2,t); bb=(s/2+s*cs,t+s*sn); c=(bb[0]+s/2+t*ct,bb[1])
    d=(c[0],c[1]-t); e=(d[0]-s/2,d[1]); f=(e[0]-s*cs,0)
    mirror_y=lambda p:(p[0],-p[1])
    mirror_x=lambda p:(-p[0],p[1])
    g,hh,i,j,k=map(mirror_y,[e,d,c,bb,a])
    right=[a,bb,c,d,e,f,g,hh,i,j,k]
    left=list(map(mirror_x,[k,j,i,hh,g,f,e,d,c,bb,a]))
    ca=(a[0]-b*ct,a[1]+b); cb=(bb[0]-b/sn,bb[1])
    coat1=[ca,cb,bb,a,mirror_x(a),mirror_x(bb),mirror_x(cb),mirror_x(ca)]
    cl=(d[0],d[1]-b); cm=(e[0]+b*ct,e[1]-b); cn=(f[0]+b/sn,0)
    coat3=[f,e,d,cl,cm,cn,mirror_y(cm),mirror_y(cl),mirror_y(d),mirror_y(e)]
    return {'units':'mm','xy_periods':[2*c[0],2*c[1]], 'z_core':[1.2,1.2+h],
            'total_solid_height':h+2.4,'backing_z':0,'port_z':h+2.4+1.25,
            'profiles_xy':{'Nomex':right+left,'coating_1':coat1,'coating_2':list(map(mirror_y,coat1)),
                           'coating_3':coat3,'coating_4':list(map(mirror_x,coat3))},
            'slabs':[{'material':'skin','z':[0,1]},{'material':'adhesive','z':[1,1.2]},
                     {'material':'adhesive','z':[1.2+h,1.4+h]},{'material':'skin','z':[1.4+h,2.4+h]}],
            'instructions':'Close each polygon, extrude through z_core; each slab spans the full xy unit cell. Periodic sides; PEC at backing_z.'}


def resolve(task, parameters):
    errors=parameters_errors(task,parameters)
    if errors: raise ValueError('; '.join(errors))
    if task['family']=='Honeycomb':
        f=task['design_space']['fixed_parameters']
        return honeycomb_profiles(f['cell_width_mm'],f['wall_thickness_mm'],f['cell_angle_deg'],parameters['coating_thickness_mm'],parameters['core_height_mm'])
    p=dict(parameters)
    if 'target_vf' in p:
        with (ROOT/'geometry/tpms_target_vf_map.csv').open(encoding='utf-8',newline='') as f:
            matches=[r for r in csv.DictReader(f) if r['topology']==p['topology'] and abs(float(r['target_vf'])-p['target_vf'])<1e-8]
        if len(matches)!=1: raise ValueError('No unique frozen volume-fraction mapping')
        p['level_half_width']=float(matches[0]['level_half_width'])
        p['achieved_vf_64']=float(matches[0]['achieved_vf_64'])
    p.update(grid=[64,64,64],center=0,unit_cell_count=[1,1,1],
             coordinates='q_i = -a/2 + (i+0.5)*a/64, i=0,...,63; x,y,z in the same basis',
             solid_rule='abs(phi(x,y,z)) <= level_half_width',backing_z=-p['period_mm']/2,
             port_z=p['period_mm']/2+p['period_mm']/8)
    return p


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task_id'); parser.add_argument('--parameters'); parser.add_argument('--out',required=True)
    args=parser.parse_args(); task=read_json(task_path(args.task_id))
    parameters=read_json(args.parameters) if args.parameters else task['initial_design']['parameters']
    Path(args.out).write_text(json.dumps(resolve(task,parameters),indent=2,allow_nan=False)+'\n',encoding='utf-8')
