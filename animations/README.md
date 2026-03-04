# Animations

Manim scenes that visualize graph coloring algorithms, Kempe chain proofs,
and the discharging method central to the Four Color Theorem.

## Subpackages

### `coloring/` — Algorithm Visualization

`coloring_animation.py` renders step-by-step videos of coloring heuristics
(Greedy, DSATUR, Smallest-Last, Random) applied to any graph in the library.
Features a Voronoi duality prologue and a real-time HUD with statistics.

```bash
python animations/coloring/coloring_animation.py RSST_001 Greedy
python animations/coloring/coloring_animation.py kempe_fritsch_1 DSATUR
```

### `kempe/` — Kempe Chain Proof Animations

Animated proofs of the inductive step of the Four Color Theorem for
degree-3, 4, and 5 vertices, plus Heawood's 1890 counterexample.

```bash
manim -pql animations/kempe/kempe_proof.py KempeProofDeg3
manim -pql animations/kempe/kempe_proof.py KempeProofDeg4
manim -pql animations/kempe/kempe_proof.py KempeProofDeg5
manim -pql animations/kempe/heawood_counterexample.py HeawoodCounterexample
```

### `discharging/` — Discharging & Unavoidability

Animated lecture module covering Euler's formula, charge assignment,
the discharging procedure, and a gallery of the 633 RSST configurations.

```bash
manim -pql animations/discharging/module1_discharging.py FullModule1
```

## Shared Configuration

All render settings, color palettes, and file paths are imported from
the project-root `config.py`.  No hardcoded paths in any animation script.

