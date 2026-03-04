#!/usr/bin/env python3
"""
generate_planar_pkls.py
========================
Control script for the Four Color Theorem graph library.

Orchestrates daughter modules that each generate a category of planar
graph objects (.pkl files). This script:

  1. Discovers and runs one or more daughter modules
  2. Saves timestamped .pkl files per module (never overwrites)
  3. Harmonizes metadata across all modules via standardized fields
  4. Detects graph isomorphisms across the full library
  5. Combines the latest .pkl from every module into a single
     all_planar_graphs.pkl (always overwritten to stay current)
  6. Provides a --display mode for quick graph inspection

Usage Examples
--------------
    # Run all modules and build combined file
    python generate_planar_pkls.py --all

    # Run only the RSST module
    python generate_planar_pkls.py --modules rsst_unavoidable

    # Run two specific modules
    python generate_planar_pkls.py --modules rsst_unavoidable kempe_counterexample

    # Rebuild combined file from existing module .pkls (no re-generation)
    python generate_planar_pkls.py --combine-only

    # Display a specific graph
    python generate_planar_pkls.py --display RSST_001

    # Display a graph and its isomorphic matches
    python generate_planar_pkls.py --display kempe_fritsch_1 --show-isomorphic

    # List all graphs in the combined library
    python generate_planar_pkls.py --list

    # List with filtering
    python generate_planar_pkls.py --list --filter-module kempe_counterexample

Author:  Tanya Wilcox
Course:  MTH-392 Senior Project, Wilkes University, Spring 2026
"""

import argparse
import importlib
import os
import pickle
import re
import sys
import textwrap
from datetime import datetime
from glob import glob
from pathlib import Path

import networkx as nx

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
# Try to import from the project-level config; fall back to script-relative
# paths so this script can still run standalone.
try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import (
        GRAPH_LIBRARY_DIR, GRAPH_LIBRARY_INPUT_DIR,
        GRAPH_LIBRARY_OUTPUT_DIR, GRAPH_LIBRARY_IMAGES_DIR,
    )
    SCRIPT_DIR = GRAPH_LIBRARY_DIR
    INPUT_DIR  = GRAPH_LIBRARY_INPUT_DIR
    OUTPUT_DIR = GRAPH_LIBRARY_OUTPUT_DIR
    IMAGES_DIR = GRAPH_LIBRARY_IMAGES_DIR
except ImportError:
    SCRIPT_DIR = Path(__file__).resolve().parent
    INPUT_DIR  = SCRIPT_DIR / "input"
    OUTPUT_DIR = SCRIPT_DIR / "output"
    IMAGES_DIR = OUTPUT_DIR / "images"

MODULES_DIR = SCRIPT_DIR / "modules"
COMBINED_FILENAME = "all_planar_graphs.pkl"

# ---------------------------------------------------------------------------
# Module registry — add new modules here
# ---------------------------------------------------------------------------
# Each entry: (module_import_path, MODULE_NAME, needs_input_dir)
MODULE_REGISTRY = [
    ("modules.generate_rsst_unavoidable_graphs", "rsst_unavoidable", True),
    ("modules.generate_kempe_counterexample_graphs", "kempe_counterexample", False),
    # --- FUTURE MODULES ---
    # ("modules.generate_networkx_famous_graphs", "networkx_famous", False),
    # ("modules.generate_fullerene_graphs", "fullerene", False),
    # ("modules.generate_geographic_maps", "geographic_maps", True),
    # ("modules.generate_polyhedra_3d", "polyhedra_3d", False),
]


# ============================================================
# Metadata harmonization
# ============================================================

def harmonize_metadata(graphs_dict, module_name):
    """
    Add standardized metadata to every graph in the dict.
    Called after each module's generate() returns.
    """
    from modules.base_module import compute_standard_metadata

    for key, G in graphs_dict.items():
        # Ensure module tag
        G.graph['module'] = module_name

        # Compute standardized measures
        std_meta = compute_standard_metadata(G)
        for field, value in std_meta.items():
            # Don't overwrite module-specific values if they exist
            if field not in G.graph:
                G.graph[field] = value
            elif field in ('vertices', 'edges'):
                # Always update computed counts to be accurate
                G.graph[field] = value

        # Ensure required fields have defaults
        G.graph.setdefault('source', module_name)
        G.graph.setdefault('name', key)
        G.graph.setdefault('short_name', key)
        G.graph.setdefault('year', None)
        G.graph.setdefault('author', None)
        G.graph.setdefault('description', '')

    return graphs_dict


# ============================================================
# Isomorphism detection
# ============================================================

def detect_isomorphisms(combined_graphs):
    """
    For each graph, find all other graphs in the library that are
    isomorphic to it. Stores the result in G.graph['isomorphic_to'].

    Uses NetworkX's VF2 algorithm. Graphs are bucketed by (V, E, sorted
    degree sequence) first to avoid unnecessary comparisons.

    Returns the number of isomorphic pairs found.
    """
    print("\n  Detecting isomorphisms across full library...")
    keys = list(combined_graphs.keys())
    n = len(keys)

    # Initialize
    for k in keys:
        combined_graphs[k].graph['isomorphic_to'] = []

    # Bucket by invariants to prune comparisons
    buckets = {}
    for k in keys:
        G = combined_graphs[k]
        v = G.number_of_nodes()
        e = G.number_of_edges()
        deg_seq = tuple(sorted((d for _, d in G.degree()), reverse=True))
        bucket_key = (v, e, deg_seq)
        buckets.setdefault(bucket_key, []).append(k)

    pairs_found = 0
    buckets_checked = 0
    multi_buckets = {k: v for k, v in buckets.items() if len(v) > 1}

    print(f"    {len(multi_buckets)} buckets with potential matches "
          f"(out of {len(buckets)} total)")

    for bucket_key, bucket_keys in multi_buckets.items():
        buckets_checked += 1
        bk_list = bucket_keys
        for i in range(len(bk_list)):
            for j in range(i + 1, len(bk_list)):
                k1, k2 = bk_list[i], bk_list[j]
                G1 = combined_graphs[k1]
                G2 = combined_graphs[k2]
                try:
                    if nx.is_isomorphic(G1, G2):
                        G1.graph['isomorphic_to'].append(k2)
                        G2.graph['isomorphic_to'].append(k1)
                        pairs_found += 1
                except Exception:
                    pass

    print(f"    Found {pairs_found} isomorphic pairs.")
    return pairs_found


# ============================================================
# Module output: save timestamped pkl per module
# ============================================================

def save_module_output(graphs_dict, module_name):
    """Save module output with timestamp. Never overwrites."""
    module_dir = OUTPUT_DIR / module_name
    module_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{module_name}_graphs_{ts}.pkl"
    out_path = module_dir / filename

    with open(out_path, 'wb') as f:
        pickle.dump(graphs_dict, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"  Saved {len(graphs_dict)} graphs → {out_path}")
    return out_path


def load_latest_module_pkl(module_name):
    """
    Find and load the most recent .pkl file from a module's output folder.
    Returns (dict, path) or (None, None) if not found.
    """
    module_dir = OUTPUT_DIR / module_name
    if not module_dir.is_dir():
        return None, None

    pkl_files = sorted(module_dir.glob(f"{module_name}_graphs_*.pkl"))
    if not pkl_files:
        return None, None

    latest = pkl_files[-1]  # Sorted by timestamp → last is newest
    with open(latest, 'rb') as f:
        data = pickle.load(f)

    return data, latest


# ============================================================
# Combined output
# ============================================================

def build_combined_pkl(run_modules=None):
    """
    Combine the latest .pkl from each registered module into one file.
    Always overwrites the combined file.

    Parameters
    ----------
    run_modules : set or None
        If provided, only these modules were just run (for logging).
    """
    combined = {}

    print("\n" + "=" * 75)
    print("Building combined library: all_planar_graphs.pkl")
    print("=" * 75)

    for _, module_name, _ in MODULE_REGISTRY:
        data, path = load_latest_module_pkl(module_name)
        if data is not None:
            # Check for key collisions
            collisions = set(data.keys()) & set(combined.keys())
            if collisions:
                print(f"  WARNING: Key collisions from {module_name}: {collisions}")
                # Prefix with module name to resolve
                data = {f"{module_name}__{k}": v for k, v in data.items()}

            combined.update(data)
            status = "← FRESH" if (run_modules and module_name in run_modules) else "← cached"
            print(f"  {module_name:30s} {len(data):>5d} graphs  {status}  ({path.name})")
        else:
            print(f"  {module_name:30s}     — graphs  (no pkl found)")

    if not combined:
        print("\n  No graphs to combine. Run with --all first.")
        return {}

    # Detect isomorphisms across the full library
    detect_isomorphisms(combined)

    # Save combined file
    combined_path = OUTPUT_DIR / COMBINED_FILENAME
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(combined_path, 'wb') as f:
        pickle.dump(combined, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"\n  Combined library: {len(combined)} graphs → {combined_path}")
    return combined


# ============================================================
# Module runner
# ============================================================

def run_module(module_import_path, module_name, needs_input):
    """Import and run a single daughter module."""
    print(f"\n{'=' * 75}")
    print(f"Module: {module_name}")
    print(f"{'=' * 75}")

    try:
        mod = importlib.import_module(module_import_path)
    except ImportError as e:
        print(f"  ERROR: Could not import {module_import_path}: {e}")
        return {}

    # Validate interface
    if not hasattr(mod, 'generate'):
        print(f"  ERROR: Module {module_name} has no generate() function.")
        return {}

    # Call generate
    kwargs = {}
    input_dir = str(INPUT_DIR) if needs_input else None
    output_dir = str(OUTPUT_DIR / module_name)

    try:
        graphs = mod.generate(
            input_dir=input_dir,
            output_dir=output_dir,
            **kwargs
        )
    except Exception as e:
        print(f"  ERROR running {module_name}: {e}")
        import traceback
        traceback.print_exc()
        return {}

    if not graphs:
        print(f"  WARNING: Module {module_name} produced 0 graphs!")
        return {}

    # Harmonize metadata
    graphs = harmonize_metadata(graphs, module_name)

    # Save timestamped pkl
    save_module_output(graphs, module_name)

    return graphs


# ============================================================
# Display / inspection
# ============================================================

def display_graph(combined, graph_key, show_isomorphic=False):
    """
    Display a graph's metadata and adjacency to the terminal.
    Optionally generates a simple HTML visualization.
    """
    if graph_key not in combined:
        # Try case-insensitive / partial match
        matches = [k for k in combined if graph_key.lower() in k.lower()]
        if len(matches) == 1:
            graph_key = matches[0]
        elif len(matches) > 1:
            print(f"Ambiguous key '{graph_key}'. Matches:")
            for m in matches[:20]:
                print(f"  {m}")
            return
        else:
            print(f"Graph '{graph_key}' not found in combined library.")
            print(f"Use --list to see available graphs.")
            return

    G = combined[graph_key]
    meta = G.graph

    print(f"\n{'=' * 60}")
    print(f"  {meta.get('name', graph_key)}")
    print(f"{'=' * 60}")
    print(f"  Key:          {graph_key}")
    print(f"  Module:       {meta.get('module', '?')}")
    print(f"  Source:        {meta.get('source', '?')}")
    print(f"  Vertices:     {G.number_of_nodes()}")
    print(f"  Edges:        {G.number_of_edges()}")
    print(f"  Planar:       {meta.get('is_planar', '?')}")
    print(f"  Connected:    {meta.get('is_connected', '?')}")
    print(f"  Bipartite:    {meta.get('is_bipartite', '?')}")
    print(f"  Tree:         {meta.get('is_tree', '?')}")
    print(f"  Density:      {meta.get('density', 0):.4f}")
    print(f"  Girth:        {meta.get('girth', '?')}")
    print(f"  Degree range: [{meta.get('min_degree', '?')}, {meta.get('max_degree', '?')}]")
    print(f"  Avg degree:   {meta.get('avg_degree', 0):.2f}")
    print(f"  χ (greedy):   {meta.get('chromatic_number_greedy', '?')}")

    if meta.get('year'):
        print(f"  Year:         {meta['year']}")
    if meta.get('author'):
        print(f"  Author:       {meta['author']}")
    if meta.get('description'):
        wrapped = textwrap.fill(meta['description'], width=55,
                                initial_indent='  ', subsequent_indent='                ')
        print(f"  Description:  {wrapped.strip()}")

    # Module-specific fields
    specific_fields = [
        'ring_size', 'configuration_number', 'weight',
        'interior_vertices', 'reducibility_value', 'n_contracts',
        'is_d_reducible', 'graph_family', 'embedding_id',
    ]
    shown_specific = False
    for field in specific_fields:
        if field in meta:
            if not shown_specific:
                print(f"\n  --- Module-Specific ---")
                shown_specific = True
            print(f"  {field:22s}: {meta[field]}")

    # Isomorphisms
    iso_list = meta.get('isomorphic_to', [])
    if iso_list:
        print(f"\n  Isomorphic to ({len(iso_list)}):")
        for iso_key in iso_list[:10]:
            iso_name = combined[iso_key].graph.get('name', iso_key) if iso_key in combined else iso_key
            print(f"    → {iso_key}  ({iso_name})")
        if len(iso_list) > 10:
            print(f"    ... and {len(iso_list) - 10} more")

    # Adjacency list
    if G.number_of_nodes() <= 30:
        print(f"\n  Adjacency List:")
        for v in sorted(G.nodes()):
            nbrs = sorted(G.neighbors(v))
            print(f"    {v:>3d} (deg {G.degree(v):2d}): {nbrs}")

    # Generate simple HTML image
    try:
        _generate_display_html(G, graph_key, meta)
    except Exception as e:
        print(f"\n  (Could not generate HTML preview: {e})")

    if show_isomorphic and iso_list:
        print(f"\n{'=' * 60}")
        print("  Isomorphic graph details:")
        for iso_key in iso_list[:5]:
            if iso_key in combined:
                display_graph(combined, iso_key, show_isomorphic=False)


def _generate_display_html(G, graph_key, meta):
    """Generate a simple HTML file with an SVG rendering of the graph."""
    pos = meta.get('pos')
    if not pos:
        print("  (No layout positions — cannot generate preview)")
        return

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    html_path = IMAGES_DIR / f"{graph_key}.html"

    # Scale positions to SVG coordinates
    width, height = 600, 600
    margin = 50
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = max(x_max - x_min, 1e-9)
    y_span = max(y_max - y_min, 1e-9)

    def scale(x, y):
        sx = margin + (x - x_min) / x_span * (width - 2 * margin)
        sy = margin + (y_max - y) / y_span * (height - 2 * margin)  # flip Y
        return sx, sy

    # Build SVG
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'style="background:#1a1a2e;">',
    ]

    # Edges
    for u, v in G.edges():
        if u in pos and v in pos:
            x1, y1 = scale(*pos[u])
            x2, y2 = scale(*pos[v])
            svg_lines.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                f'x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#4a9eff" stroke-width="1.5" opacity="0.6"/>'
            )

    # Nodes
    node_radius = max(4, min(12, 200 // max(G.number_of_nodes(), 1)))
    for node in sorted(G.nodes()):
        if node in pos:
            cx, cy = scale(*pos[node])
            svg_lines.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{node_radius}" '
                f'fill="#e94560" stroke="#fff" stroke-width="1"/>'
            )
            if G.number_of_nodes() <= 30:
                svg_lines.append(
                    f'<text x="{cx:.1f}" y="{cy + 3:.1f}" '
                    f'text-anchor="middle" fill="#fff" '
                    f'font-size="10" font-family="monospace">{node}</text>'
                )

    svg_lines.append('</svg>')
    svg_content = '\n'.join(svg_lines)

    # Build full HTML
    title = meta.get('name', graph_key)
    info_lines = [
        f"Vertices: {G.number_of_nodes()} | Edges: {G.number_of_edges()}",
        f"Planar: {meta.get('is_planar')} | Connected: {meta.get('is_connected')}",
        f"Degree range: [{meta.get('min_degree')}, {meta.get('max_degree')}]",
    ]
    if meta.get('year'):
        info_lines.append(f"Year: {meta['year']} | Author: {meta.get('author', '?')}")
    if meta.get('ring_size'):
        info_lines.append(
            f"Ring: {meta['ring_size']} | Interior: {meta.get('interior_vertices')} | "
            f"D-reducible: {meta.get('is_d_reducible')}"
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ background: #0f0f23; color: #ccc; font-family: 'Consolas', monospace;
         display: flex; flex-direction: column; align-items: center; padding: 20px; }}
  h1 {{ color: #e94560; margin-bottom: 5px; }}
  .info {{ color: #8892b0; font-size: 13px; margin: 3px 0; }}
  .key {{ color: #4a9eff; font-size: 12px; }}
</style>
</head><body>
<h1>{title}</h1>
<p class="key">{graph_key}</p>
{"".join(f'<p class="info">{line}</p>' for line in info_lines)}
{svg_content}
</body></html>"""

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n  Preview saved: {html_path}")
    print(f"  Open in browser to view.")


def list_graphs(combined, filter_module=None, filter_source=None):
    """Print a formatted table of all graphs in the library."""
    if not combined:
        print("No graphs in library. Run with --all first.")
        return

    # Apply filters
    filtered = combined
    if filter_module:
        filtered = {k: v for k, v in filtered.items()
                    if v.graph.get('module') == filter_module}
    if filter_source:
        filtered = {k: v for k, v in filtered.items()
                    if v.graph.get('source') == filter_source}

    print(f"\n{'Key':<35s} {'Name':<35s} {'V':>3s} {'E':>3s} "
          f"{'Module':<25s} {'Iso':>3s}")
    print("-" * 110)

    for key in sorted(filtered.keys()):
        g = filtered[key]
        m = g.graph
        n_iso = len(m.get('isomorphic_to', []))
        iso_str = str(n_iso) if n_iso > 0 else ""
        print(f"{key:<35s} {m.get('name', '?'):<35s} "
              f"{m.get('vertices', 0):>3d} {m.get('edges', 0):>3d} "
              f"{m.get('module', '?'):<25s} {iso_str:>3s}")

    print(f"\nTotal: {len(filtered)} graphs")
    if filter_module or filter_source:
        print(f"(filtered from {len(combined)} total)")


# ============================================================
# CLI
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        description="Four Color Theorem — Planar Graph Library Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python generate_planar_pkls.py --all
          python generate_planar_pkls.py --modules rsst_unavoidable
          python generate_planar_pkls.py --combine-only
          python generate_planar_pkls.py --display RSST_001
          python generate_planar_pkls.py --list
          python generate_planar_pkls.py --list --filter-module kempe_counterexample
        """)
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--all', action='store_true',
        help='Run ALL registered modules and rebuild combined file.'
    )
    group.add_argument(
        '--modules', nargs='+', metavar='NAME',
        help='Run specific module(s) by name, then rebuild combined file.'
    )
    group.add_argument(
        '--combine-only', action='store_true',
        help='Skip generation; just rebuild combined file from existing .pkls.'
    )
    group.add_argument(
        '--display', metavar='GRAPH_KEY',
        help='Display metadata and adjacency for a specific graph.'
    )
    group.add_argument(
        '--list', action='store_true',
        help='List all graphs in the combined library.'
    )

    parser.add_argument(
        '--show-isomorphic', action='store_true',
        help='With --display, also show details of isomorphic graphs.'
    )
    parser.add_argument(
        '--filter-module', metavar='MODULE',
        help='With --list, filter by module name.'
    )
    parser.add_argument(
        '--filter-source', metavar='SOURCE',
        help='With --list, filter by source tag.'
    )
    parser.add_argument(
        '--input-dir', metavar='DIR',
        help='Override the input directory (default: ./input/)'
    )
    parser.add_argument(
        '--output-dir', metavar='DIR',
        help='Override the output directory (default: ./output/)'
    )
    parser.add_argument(
        '--skip-isomorphism', action='store_true',
        help='Skip isomorphism detection (faster for large libraries).'
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Override directories if specified
    global INPUT_DIR, OUTPUT_DIR, IMAGES_DIR
    if args.input_dir:
        INPUT_DIR = Path(args.input_dir).resolve()
    if args.output_dir:
        OUTPUT_DIR = Path(args.output_dir).resolve()
        IMAGES_DIR = OUTPUT_DIR / "images"

    # Ensure directories exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Display mode ---
    if args.display:
        combined_path = OUTPUT_DIR / COMBINED_FILENAME
        if not combined_path.is_file():
            print(f"Combined library not found at {combined_path}")
            print("Run with --all first to generate it.")
            sys.exit(1)
        with open(combined_path, 'rb') as f:
            combined = pickle.load(f)
        display_graph(combined, args.display, args.show_isomorphic)
        return

    # --- List mode ---
    if args.list:
        combined_path = OUTPUT_DIR / COMBINED_FILENAME
        if not combined_path.is_file():
            print(f"Combined library not found at {combined_path}")
            print("Run with --all first to generate it.")
            sys.exit(1)
        with open(combined_path, 'rb') as f:
            combined = pickle.load(f)
        list_graphs(combined,
                     filter_module=args.filter_module,
                     filter_source=args.filter_source)
        return

    # --- Combine-only mode ---
    if args.combine_only:
        build_combined_pkl()
        return

    # --- Generation mode ---
    print("=" * 75)
    print("  Four Color Theorem — Planar Graph Library Builder")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)
    print(f"  Input dir:  {INPUT_DIR}")
    print(f"  Output dir: {OUTPUT_DIR}")

    # Determine which modules to run
    if args.all:
        modules_to_run = [
            (imp, name, needs_input)
            for imp, name, needs_input in MODULE_REGISTRY
        ]
    elif args.modules:
        name_set = set(args.modules)
        modules_to_run = [
            (imp, name, needs_input)
            for imp, name, needs_input in MODULE_REGISTRY
            if name in name_set
        ]
        unknown = name_set - {name for _, name, _ in modules_to_run}
        if unknown:
            print(f"\n  WARNING: Unknown modules: {unknown}")
            print(f"  Available: {[name for _, name, _ in MODULE_REGISTRY]}")
    else:
        parser.print_help()
        return

    if not modules_to_run:
        print("No modules selected. Nothing to do.")
        return

    # Add the script directory to sys.path so modules can import each other
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))

    # Run selected modules
    run_names = set()
    total_graphs = 0
    for imp_path, mod_name, needs_input in modules_to_run:
        graphs = run_module(imp_path, mod_name, needs_input)
        total_graphs += len(graphs)
        if graphs:
            run_names.add(mod_name)

    print(f"\n  Modules completed: {len(run_names)}/{len(modules_to_run)}")
    print(f"  Total new graphs: {total_graphs}")

    # Build combined pkl
    combined = build_combined_pkl(run_modules=run_names)

    # Final summary
    if combined:
        print(f"\n{'=' * 75}")
        print(f"  DONE — {len(combined)} graphs in combined library")
        print(f"  File: {OUTPUT_DIR / COMBINED_FILENAME}")
        print(f"{'=' * 75}")

        # Module breakdown
        module_counts = {}
        for g in combined.values():
            m = g.graph.get('module', 'unknown')
            module_counts[m] = module_counts.get(m, 0) + 1
        print(f"\n  Module breakdown:")
        for m, c in sorted(module_counts.items()):
            print(f"    {m:30s} {c:>5d} graphs")

        # Isomorphism summary
        iso_graphs = sum(
            1 for g in combined.values()
            if g.graph.get('isomorphic_to')
        )
        if iso_graphs:
            print(f"\n  Graphs with isomorphic matches: {iso_graphs}")


if __name__ == "__main__":
    main()
