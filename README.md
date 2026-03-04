# Four Color Theorem — Animated Exploration

**Author:** Tanya Wilcox  

**Institution:** Wilkes University  

**Course:** MTH-392 — Senior Project in Computational Mathematics, Spring 2026  


---

## Overview

This project is a computational and visual investigation of the
[Four Color Theorem](https://en.wikipedia.org/wiki/Four_color_theorem) (4CT),
which states that the regions of every planar map can be colored with at most
four colors so that no two adjacent regions share the same color.

The project uses the [Manim](https://www.manim.community/) animation library
to produce step-by-step videos showing how graph-coloring heuristics
(Greedy, DSATUR, Smallest-Last) assign colors to planar graphs drawn from a
curated library of mathematically significant examples.


### What's Included

| Component | Description |
|---|---|
| **Graph Library** | A modular pipeline that parses the 633 RSST unavoidable configurations and 19 Kempe counterexample graphs into a unified pickle file. Extensible via "daughter modules." |
| **Coloring Animations** | Manim scenes that animate Greedy, DSATUR, Smallest-Last, and Random coloring heuristics on any graph in the library, complete with a Voronoi duality prologue and real-time HUD. |
| **Kempe Proof Animations** | Step-by-step animated proofs of the Kempe chain argument for degree-3, 4, and 5 vertices, culminating in Heawood's 1890 counterexample showing where Kempe's original proof fails. |
| **Discharging Module** | Animated demonstration of the discharging method used by Robertson–Sanders–Seymour–Thomas (1997) to prove unavoidability of their 633 configurations. |
| **Video Tools** | Utility scripts to combine per-algorithm videos side-by-side for comparison. |


## Project Structure

```
four-color-theorem/
│
├── config.py                    # Centralized paths, palettes, render settings
├── .env.example                 # Template — copy to .env, edit your paths
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Modern Python packaging metadata
│
├── graph_library/               # Graph generation pipeline
│   ├── generate_planar_pkls.py      # Orchestrator — runs modules, builds combined pkl
│   ├── input/                       # Raw data files (unavoidable.conf)
│   ├── output/                      # Generated .pkl files and images (gitignored)
│   └── modules/                     # Daughter modules (one per graph family)
│       ├── base_module.py
│       ├── generate_rsst_unavoidable_graphs.py
│       └── generate_kempe_counterexample_graphs.py
│
├── animations/                  # Manim animation scripts
│   ├── coloring/
│   │   └── coloring_animation.py    # Algorithm visualization + duality prologue
│   ├── kempe/
│   │   ├── kempe_common.py          # Shared Kempe chain utilities
│   │   ├── kempe_proof.py           # Degree-3, 4, 5 induction scenes
│   │   ├── kempe_module1.py         # Extended Kempe lecture module
│   │   └── heawood_counterexample.py    # Heawood 1890 failure demonstration
│   └── discharging/
│       └── module1_discharging.py   # Euler charges + unavoidability argument
│
└── tools/                       # Utility scripts
    └── combine_algorithm_videos.py
```


## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/four-color-theorem.git
cd four-color-theorem
pip install -r requirements.txt
```

> **Note:** Manim requires system-level dependencies (ffmpeg, LaTeX, cairo).
> See the [Manim installation guide](https://docs.manim.community/en/stable/installation.html).

### 2. Configure paths

```bash
cp .env.example .env
# Edit .env to match your machine's directory layout
```

### 3. Build the graph library

Place `unavoidable.conf` in `graph_library/input/`, then:

```bash
cd graph_library
python generate_planar_pkls.py --all
```

This parses the RSST configurations and Kempe counterexample graphs,
computes layouts, detects isomorphisms, and writes `all_planar_graphs.pkl`.

### 4. Render an animation

```bash
# Coloring algorithm animation
python animations/coloring/coloring_animation.py RSST_001 Greedy

# List available graphs
python animations/coloring/coloring_animation.py --list
python animations/coloring/coloring_animation.py --list kempe

# Kempe proof scenes
manim -pql animations/kempe/kempe_proof.py KempeProofDeg3

# Discharging lecture
manim -pql animations/discharging/module1_discharging.py FullModule1
```

### 5. Compare algorithms side-by-side

```bash
python tools/combine_algorithm_videos.py kempe_fritsch_1 DSATUR Greedy SmlLst
```


## Coloring Algorithms

The main animation script (`coloring_animation.py`) supports four heuristics:

| Algorithm | Strategy | Backtracking? |
|---|---|---|
| **Greedy** | Largest-degree-first ordering | Yes (4-color) |
| **DSATUR** | Saturation-degree priority (Brelaz, 1979) | Fallback if >4 colors needed |
| **SmlLst** | Smallest-last elimination ordering | Yes (4-color) |
| **Random** | Uniformly random vertex ordering | No (may use >4 colors) |

Each run produces an MP4 video, a JSON metadata file, and a row in a
cumulative CSV leaderboard for cross-algorithm comparison.


## Mathematical Background

The Four Color Theorem was first proved by Appel & Haken (1977) using
computer-verified reducibility of 1,482 configurations.  Robertson, Sanders,
Seymour & Thomas (1997) simplified the proof to 633 configurations.
Gonthier (2008) formalized the entire argument in the Coq proof assistant.

This project visualizes three pillars of the proof:

1. **Unavoidability** — The discharging method shows that every minimal
   counterexample must contain at least one of the 633 configurations.
2. **Reducibility** — Each configuration is proved reducible, meaning it
   cannot appear in a minimal counterexample.
3. **Kempe chains** — The classical technique for extending partial colorings,
   including Heawood's demonstration of where Kempe's original 1879 argument
   breaks down for degree-5 vertices.


## Key References

1. K. Appel & W. Haken, "Every Planar Map is Four Colorable," *Illinois J. Math.*, 1977.
2. N. Robertson, D. P. Sanders, P. D. Seymour & R. Thomas, "The Four-Colour Theorem," *J. Combin. Theory Ser. B*, 1997.
3. G. Gonthier, "Formal Proof — The Four-Color Theorem," *Notices of the AMS*, 2008.
4. A. B. Kempe, "On the Geographical Problem of the Four Colours," *Amer. J. Math.*, 1879.
5. P. J. Heawood, "Map-Colour Theorem," *Quart. J. Pure Appl. Math.*, 1890.
6. D. Brelaz, "New Methods to Color the Vertices of a Graph," *Commun. ACM*, 1979.


## License

This project was developed as an academic senior project.  Source code is
released under the [MIT License](LICENSE).  The RSST `unavoidable.conf` data
file is derived from the original authors' publicly available proof materials.

