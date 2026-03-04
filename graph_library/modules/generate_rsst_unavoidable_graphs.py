#!/usr/bin/env python3
"""
generate_rsst_unavoidable_graphs.py
====================================
Daughter module: parses the RSST unavoidable.conf file and produces
633 graph objects representing the unavoidable set from Robertson,
Sanders, Seymour, and Thomas (1997).

Each graph preserves all data from the original configuration file:
    - weight (the real number header)
    - ring_size (boundary cycle length)
    - reducibility_value (number of bad colorings remaining)
    - contracts (list of vertex-pair identifications)
    - reducibility_data (raw integer array used by reduce.c)
    - full adjacency structure with vertex degrees

Module-specific metadata stored in G.graph:
    configuration_number  : int    — 1-indexed position in the file
    weight                : float  — RSST weight / priority value
    ring_size             : int    — size of the boundary ring
    interior_vertices     : int    — vertices inside the ring
    reducibility_value    : int    — # bad colorings after reduction
    n_contracts           : int    — number of contract pairs
    contracts             : list   — [(v1,u1), (v2,u2), ...] pairs
    reducibility_data     : list   — raw integers from reduce.c format
    vertex_degrees        : dict   — {vertex_id: degree} from the file
    is_d_reducible        : bool   — True if reducibility_value == 0
                                     and n_contracts == 0
    source                : str    — 'RSST'

References:
    Robertson, Sanders, Seymour & Thomas,
    "The Four-Colour Theorem" (JCTB, 1997)
"""

import os
import re
import math
import networkx as nx
import numpy as np
from modules.base_module import compute_layouts, verify_graph, normalize_pos

# ---- Module Interface ----
MODULE_NAME = "rsst_unavoidable"
MODULE_DESCRIPTION = (
    "633 configurations from the RSST unavoidable set "
    "(Robertson, Sanders, Seymour & Thomas, 1997)"
)


def generate(input_dir, output_dir=None, **kwargs):
    """
    Parse unavoidable.conf and return a dict of {short_name: nx.Graph}.

    Parameters
    ----------
    input_dir : str
        Directory containing 'unavoidable.conf' (or the filename given
        by kwargs['config_filename']).
    output_dir : str, optional
        Not used directly by this module (control script handles saving).
    **kwargs :
        config_filename : str — override the input filename
                                (default: 'unavoidable.conf')

    Returns
    -------
    dict[str, nx.Graph]
    """
    config_filename = kwargs.get('config_filename', 'unavoidable.conf')
    # Also check for .txt extension variant
    input_path = os.path.join(input_dir, config_filename)
    if not os.path.isfile(input_path):
        alt_path = os.path.join(input_dir, config_filename.replace('.conf', '_conf.txt'))
        if os.path.isfile(alt_path):
            input_path = alt_path
        else:
            # Try just the txt version
            alt_path2 = os.path.join(input_dir, 'unavoidable_conf.txt')
            if os.path.isfile(alt_path2):
                input_path = alt_path2
            else:
                print(f"  ERROR: Could not find config file in {input_dir}")
                print(f"         Tried: {config_filename}, "
                      f"{config_filename.replace('.conf', '_conf.txt')}, "
                      f"unavoidable_conf.txt")
                return {}

    print(f"  Parsing: {input_path}")
    graphs = _parse_unavoidable_config(input_path)

    if not graphs:
        print("  WARNING: No graphs parsed from config file.")
        return {}

    # Compute layouts for each graph
    print(f"  Computing layouts for {len(graphs)} configurations...")
    result = {}
    for key, G in graphs.items():
        # Use a deterministic seed based on config number
        cfg_num = G.graph['configuration_number']

        # Compute spring layout seeded from planar embedding for visual clarity.
        # The planar combinatorial embedding gives topologically correct positions
        # but spring layout produces much more readable node spacing.
        n = max(1, G.number_of_nodes())
        try:
            pos_seed = nx.planar_layout(G)
        except Exception:
            pos_seed = None

        pos = nx.spring_layout(
            G, seed=1000 + cfg_num, pos=pos_seed,
            k=2.0 / math.sqrt(n),
            iterations=300,
        )
        G.graph['pos'] = normalize_pos(pos)
        result[key] = G

        # Progress indicator every 100 graphs
        if cfg_num % 100 == 0:
            print(f"    ... layout {cfg_num}/{len(graphs)}")

    print(f"  Generated {len(result)} RSST configurations with layouts.")
    return result


def _parse_unavoidable_config(path):
    """
    Parse the RSST unavoidable.conf format into a dict of NetworkX graphs.

    File format per configuration:
        Line 1: weight (float, e.g. "0.7322")
        Line 2: n_vertices  ring_size  reducibility_value  n_contracts
        Line 3: contract line — starts with count, then pairs
                 OR "0" if no contracts
        Lines 4..4+n-1: adjacency — vertex_id  degree  neighbor1 neighbor2 ...
        Remaining lines until blank: reducibility data (space-separated ints)
        Blank line: separator
    """
    with open(path, encoding='utf-8') as f:
        lines = [line.rstrip() for line in f]

    graphs = {}
    i = 0
    config_count = 0

    while i < len(lines):
        # Skip blank lines
        if not lines[i].strip():
            i += 1
            continue

        # --- Line 1: weight ---
        weight_match = re.match(r'^[\s]*(\d+\.?\d*)', lines[i].strip())
        if not weight_match:
            i += 1
            continue

        # Check if this is actually a weight line (float with decimal) or
        # could be an adjacency line. Weight lines are standalone floats.
        stripped = lines[i].strip()
        parts = stripped.split()

        # A weight line has exactly one token that contains a decimal point,
        # OR it's a pure float. Adjacency lines have vertex_id degree neighbors...
        if len(parts) == 1 and '.' in parts[0]:
            try:
                weight = float(parts[0])
            except ValueError:
                # Handle malformed entries like "26359322.-7322"
                # Try to extract a usable weight; fall back to 0.0
                clean = re.sub(r'\.-', '.', parts[0])
                try:
                    weight = float(clean)
                except ValueError:
                    weight = 0.0
                print(f"    Note: Malformed weight '{parts[0]}' on line {i+1}, "
                      f"using {weight}")
        elif len(parts) == 1:
            # Could be a weight like "0" — skip, not a config start
            i += 1
            continue
        else:
            # Not a weight line
            i += 1
            continue

        # --- Line 2: header ---
        i += 1
        if i >= len(lines):
            break

        header_parts = lines[i].split()
        if len(header_parts) < 4:
            continue

        try:
            n_vertices = int(header_parts[0])
            ring_size = int(header_parts[1])
            reducibility_value = int(header_parts[2])
            n_contracts_raw = int(header_parts[3])
        except (ValueError, IndexError):
            continue

        # --- Line 3: contract line ---
        i += 1
        if i >= len(lines):
            break

        contract_line = lines[i].strip()
        contracts = []

        if contract_line == '0' or contract_line == '':
            # No contracts — line is just "0" or blank
            pass
        else:
            contract_tokens = contract_line.split()
            try:
                n_contract_pairs = int(contract_tokens[0])
                # Pairs follow: v1 u1 v2 u2 ...
                for ci in range(n_contract_pairs):
                    v_c = int(contract_tokens[1 + 2 * ci])
                    u_c = int(contract_tokens[2 + 2 * ci])
                    contracts.append((v_c, u_c))
            except (ValueError, IndexError):
                pass

        # --- Lines 4..4+n-1: adjacency ---
        i += 1
        G = nx.Graph()
        vertex_degrees = {}
        ring_vertices = list(range(1, ring_size + 1))  # Ring is vertices 1..ring_size
        interior_start = ring_size + 1

        for j in range(n_vertices):
            if i + j >= len(lines):
                break

            tokens = lines[i + j].split()
            if not tokens:
                continue

            try:
                v = int(tokens[0])
                degree = int(tokens[1])
                G.add_node(v)
                vertex_degrees[v] = degree

                # Neighbors start at index 2
                neighbors = []
                for t in tokens[2:]:
                    try:
                        neighbors.append(int(t))
                    except ValueError:
                        pass

                for u in neighbors:
                    if u != v:  # avoid self-loops
                        G.add_edge(v, u)

            except (ValueError, IndexError):
                continue

        i += n_vertices

        # --- Remaining lines until blank: reducibility data ---
        reducibility_data = []
        while i < len(lines) and lines[i].strip():
            for token in lines[i].split():
                try:
                    reducibility_data.append(int(token))
                except ValueError:
                    pass
            i += 1

        # --- Build the graph metadata ---
        config_count += 1
        short_name = f"RSST_{config_count:03d}"

        interior_vertices = n_vertices - ring_size
        is_d_reducible = (n_contracts_raw == 0)

        G.graph.update({
            'name': f"RSST Config {config_count}",
            'short_name': short_name,
            'source': 'RSST',
            'configuration_number': config_count,
            'weight': weight,
            'ring_size': ring_size,
            'n_total_vertices': n_vertices,
            'interior_vertices': interior_vertices,
            'ring_vertex_ids': ring_vertices,
            'interior_vertex_ids': list(range(interior_start, n_vertices + 1)),
            'reducibility_value': reducibility_value,
            'n_contracts': len(contracts),
            'n_contracts_raw': n_contracts_raw,
            'contracts': contracts,
            'reducibility_data': reducibility_data,
            'vertex_degrees': vertex_degrees,
            'is_d_reducible': is_d_reducible,
            'author': 'N. Robertson, D. P. Sanders, P. D. Seymour, R. Thomas',
            'year': 1997,
            'description': (
                f"Configuration {config_count} from the RSST unavoidable set. "
                f"Ring size {ring_size}, {interior_vertices} interior vertices, "
                f"weight {weight:.4f}."
                + (" D-reducible." if is_d_reducible
                   else f" C-reducible with {len(contracts)} contract pair(s).")
            ),
        })

        graphs[short_name] = G

    print(f"  Parsed {config_count} configurations from file.")
    return graphs


# ============================================================
# Standalone execution (for testing / direct use)
# ============================================================
if __name__ == "__main__":
    import pickle
    from datetime import datetime

    # Default paths for standalone testing
    default_input = os.path.join(os.path.dirname(__file__), '..', 'input')
    default_output = os.path.join(os.path.dirname(__file__), '..', 'output', 'rsst_unavoidable')

    print("=" * 75)
    print("RSST Unavoidable Graphs — Standalone Mode")
    print("=" * 75)

    graphs = generate(default_input)

    if graphs:
        os.makedirs(default_output, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(default_output, f"rsst_unavoidable_graphs_{ts}.pkl")
        with open(out_path, 'wb') as f:
            pickle.dump(graphs, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"\nSaved {len(graphs)} graphs → {out_path}")

        # Summary
        ring_sizes = [g.graph['ring_size'] for g in graphs.values()]
        print(f"\nRing size distribution:")
        for rs in sorted(set(ring_sizes)):
            count = ring_sizes.count(rs)
            print(f"  Ring {rs:2d}: {count:3d} configurations")

        d_red = sum(1 for g in graphs.values() if g.graph['is_d_reducible'])
        c_red = len(graphs) - d_red
        print(f"\nD-reducible: {d_red}  |  C-reducible: {c_red}")
    else:
        print("No graphs generated.")
