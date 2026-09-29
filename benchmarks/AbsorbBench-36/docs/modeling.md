# Geometry, materials and numerical profile

All dimensions are millimetres, frequencies GHz, angles degrees and Debye relaxation times ns. Use exp(+jωt), relative permeability 1 and a single-pole permittivity:

```text
epsilon(f) = epsilon_inf + (epsilon_static - epsilon_inf)/(1 + j*2*pi*f_GHz*tau_ns)
```

`materials.json` contains the fixed material values. Honeycomb coating parameters are design variables; TPMS uses the task-specific subset of M2–M8. Do not add M1 to the allowed design space.

## Honeycomb sandwich

From the PEC backing at z=0 upwards: skin (1.0), adhesive (0.2), coated honeycomb core (height h), adhesive (0.2), skin (1.0), air (1.25), Floquet port. The full solid thickness is h+2.4.

The field named `cell_width_mm` in a task is the wall-side parameter s of the frozen geometry, **not the total periodic cell width**. With wall parameter t=`wall_thickness_mm` and α=`cell_angle_deg`=60°, the rectangular periods are:

```text
Lx = 2 * [s*(1+cos(alpha)) + t*cot(alpha)]
Ly = 2 * [t + s*sin(alpha)]
```

Use `tools/geometry.py` to obtain the exact wall polygon and four single-side coating polygons for any legal design. Close each xy polygon and extrude it from z=1.2 to z=1.2+h. The output also defines both skins and adhesive slabs over the full rectangular cell. The geometry retains the frozen wall-junction construction, rather than replacing it with a generic hexagonal lattice.

Nomex wall: εr=3.8, tanδ=0.015; skin: εr=3.3, tanδ=0.015; adhesive: εr=3.4, tanδ=0.015. Apply the task's Debye coating to the four coating regions.

## TPMS

Use one cubic period a, spanning [-a/2,a/2] on x,y,z, with X=2πx/a, Y=2πy/a, Z=2πz/a:

```text
Primitive: phi = cos(X) + cos(Y) + cos(Z)
Gyroid:    phi = sin(X)*cos(Y) + sin(Y)*cos(Z) + sin(Z)*cos(X)
Diamond:   phi = sin(X)*sin(Y)*sin(Z) + sin(X)*cos(Y)*cos(Z)
                + cos(X)*sin(Y)*cos(Z) + cos(X)*cos(Y)*sin(Z)
```

The solid is `abs(phi) <= level_half_width`, sampled at **64³ voxel centres**. Fill each occupied voxel as a brick of size a/64. The voxel centre on each axis is `-a/2 + (i+0.5)*a/64`, i=0,…,63. Preserve the xyz orientation. The PEC boundary is at z=-a/2 and the top air gap is a/8. No skins or adhesive are included.

Three development tasks use `LEVEL_LEGACY`: optimize the level half-width directly. All other TPMS tasks use `TARGET_VF_V1`: choose `target_vf` on the 0.01 grid within the task bounds, then look up its frozen level in `geometry/tpms_target_vf_map.csv`. Do not treat the level as an additional independent variable. The map covers 81 fractions for each of three topologies; it is geometric calibration, not absorption or agent-performance data. Use the recorded level rather than selecting a new quantile; voxel comparisons near floating-point ties can differ across math libraries, so verify the achieved volume fraction when porting geometry code.

## Reference full-wave settings

| Setting | Honeycomb | TPMS |
|---|---|---|
| Solver | CST Studio Suite 2025 frequency-domain FEM | Same |
| Lateral boundaries | Periodic/unit cell x,y | Same |
| Bottom | PEC electric boundary | Same |
| Top | Floquet port above air gap | Same |
| Incidence | Task θ; azimuth 0° | Same |
| Registered modes | TE00 and TM00 | Same |
| Exports | Complex co/cross reflection for each incident mode | Same |
| Solve/export band | 2–18 GHz | 2–18 GHz |
| Uniform exported grid | 1001 points | 1009 points |
| Broadband minimum samples | 15 | 15 |
| Frequency sample interval setting | Automatic, 50 | Automatic, 50 |
| Mesh | Second-order tetrahedra; near/far 17/1; nonadaptive | Same |
| AccuracyTet | 1e-4 | 1e-3 |

The export grid is uniform including both endpoints; step size is 16/(N−1) GHz. All task-band endpoints lie on the relevant grid. This dense export grid is distinct from the broadband solver's internal sampling count.

A solver adapter must create the geometry, apply the material model and fixed numerical profile, run the solver, establish actual convergence and map incident/reflected modes correctly. The portable geometry helper does not itself create a CST project or run CST. A different solver/mesh should be reported as an implementation variant and checked for numerical comparability.
