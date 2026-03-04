# Graph Library

Modular pipeline for generating a unified library of mathematically
significant planar graphs stored as NetworkX objects in pickle format.

## Architecture

```
graph_library/
├── generate_planar_pkls.py        # Orchestrator script
├── input/                         # Raw data files
│   └── unavoidable.conf           # RSST 633 configs (user-provided)
├── output/                        # Generated files (gitignored)
│   ├── all_planar_graphs.pkl      # Combined library
│   ├── rsst_unavoidable/          # Per-module timestamped .pkl files
│   └── kempe_counterexample/
└── modules/                       # Daughter modules
    ├── base_module.py             # Shared interface + layout utilities
    ├── generate_rsst_unavoidable_graphs.py
    └── generate_kempe_counterexample_graphs.py
```

## Usage

```bash
# Build everything
python generate_planar_pkls.py --all

# Run one module
python generate_planar_pkls.py --modules rsst_unavoidable

# Rebuild combined pkl from cached module outputs
python generate_planar_pkls.py --combine-only

# Inspect a graph
python generate_planar_pkls.py --display RSST_001

# List all graphs
python generate_planar_pkls.py --list
```

## Adding a New Module

1. Create `modules/generate_your_module.py`
2. Define `MODULE_NAME`, `MODULE_DESCRIPTION`, and `generate(input_dir, output_dir, **kwargs)`
3. Register it in `MODULE_REGISTRY` inside `generate_planar_pkls.py`
4. Run `python generate_planar_pkls.py --modules your_module`

See `modules/base_module.py` for the interface contract.

## Obtaining Input Data

The `unavoidable.conf` file contains the 633 RSST configurations and must
be placed in `input/` before building.  It is available from the original
authors' proof materials (Robertson, Sanders, Seymour & Thomas, 1997). https://thomas.math.gatech.edu/OLDFTP/four/unavoidable.conf

