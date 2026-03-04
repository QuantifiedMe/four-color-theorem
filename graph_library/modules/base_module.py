#!/usr/bin/env python3
"""
base_module.py
==============
Shared utilities and interface contract for all graph-generation daughter modules.


MODULE INTERFACE CONTRACT
=========================
Every daughter module MUST define:
    MODULE_NAME        : str
    MODULE_DESCRIPTION : str
    generate(input_dir, output_dir, **kwargs) -> dict[str, nx.Graph]

Each graph MUST have in G.graph:
    'name'       : str   — display title
    'short_name' : str   — unique key
    'pos'        : dict  — {node: (x, y)} layout for Manim rendering
    'source'     : str   — category tag

The control script will automatically add:
    module, vertices, edges, is_planar, is_connected, degree_sequence,
    min_degree, max_degree, avg_degree, density, is_bipartite, is_tree,
    girth, chromatic_number_greedy, isomorphic_to

Naming conventions:
    - Script: generate_[category]_graphs.py
    - Keys:   [PREFIX]_[name]_[number] (e.g. "fullerene_C60_1")
    - PKL:    [category]_graphs_YYYYMMDD_HHMMSS.pkl

After creating the module, register it in generate_planar_pkls.py's
MODULE_REGISTRY list.

Rendering note: graphs are rendered in Manim (coloring_animation.py) in a
square viewport. Layouts should fit comfortably — avoid graphs with so
many nodes that they become illegible. Use spring_layout or planar layout
to ensure edges don't overlap visually.

Modules MAY add any additional module-specific metadata freely.
"""

import math
import networkx as nx
import numpy as np


# ============================================================
# Layout computation
# ============================================================

def normalize_pos(pos, scale=5.0, max_aspect_ratio=1.6):
    """
    Normalize positions to fit in [-scale/2, scale/2] x [-scale/2, scale/2].
    Compatible with Manim's coordinate system.

    X and Y are scaled **independently** so the layout fills the target
    square in both dimensions.  This prevents wide, flat planar embeddings
    (common in combinatorial layouts) from rendering as squished isosceles
    triangles.

    To avoid extreme distortion, the ratio between the two scale factors
    is clamped to *max_aspect_ratio* (default 1.6, i.e. at most 60 %
    more stretch on one axis than the other).
    """
    if not pos:
        return pos
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    x_span = max(max(xs) - min(xs), 1e-9)
    y_span = max(max(ys) - min(ys), 1e-9)

    sx = scale / x_span
    sy = scale / y_span

    # Clamp so neither axis is stretched more than max_aspect_ratio×
    # relative to the other — keeps the topology readable.
    ratio = sy / sx if sx > 1e-12 else 1.0
    if ratio > max_aspect_ratio:
        sy = sx * max_aspect_ratio
    elif ratio < 1.0 / max_aspect_ratio:
        sx = sy * max_aspect_ratio

    return {n: ((x - cx) * sx, (y - cy) * sy) for n, (x, y) in pos.items()}


def build_shells(G):
    """Build concentric shell ordering via BFS from a peripheral vertex."""
    if G.number_of_nodes() == 0:
        return None
    start = min(G.nodes(), key=lambda v: G.degree(v))
    shells = []
    visited = set()
    frontier = {start}
    while frontier:
        shell = sorted(frontier)
        shells.append(shell)
        visited.update(frontier)
        next_frontier = set()
        for v in frontier:
            for u in G.neighbors(v):
                if u not in visited:
                    next_frontier.add(u)
        frontier = next_frontier
    return shells if len(shells) > 1 else None


def compute_layouts(G, n_layouts, seed=42):
    """
    Generate n_layouts different 2D position dictionaries for graph G.
    Returns a list of dicts {node: (x, y)}.
    """
    layouts = []
    rng = np.random.RandomState(seed)

    # 1. Planar layout (if graph is planar)
    is_planar, embedding = nx.check_planarity(G)
    if is_planar:
        try:
            pos = nx.combinatorial_embedding_to_pos(embedding)
            layouts.append(normalize_pos(pos))
        except Exception:
            pass

    # 2. Spring / Fruchterman-Reingold with different seeds
    for s in rng.randint(0, 100000, size=max(0, n_layouts - 3)):
        pos = nx.spring_layout(G, seed=int(s), iterations=200)
        layouts.append(normalize_pos(pos))

    # 3. Kamada-Kawai
    try:
        pos = nx.kamada_kawai_layout(G)
        layouts.append(normalize_pos(pos))
    except Exception:
        pos = nx.spring_layout(G, seed=seed + 999, iterations=200)
        layouts.append(normalize_pos(pos))

    # 4. Shell layout
    shells = build_shells(G)
    if shells:
        pos = nx.shell_layout(G, nlist=shells)
        layouts.append(normalize_pos(pos))

    # 5. Spectral layout
    try:
        pos = nx.spectral_layout(G)
        layouts.append(normalize_pos(pos))
    except Exception:
        pos = nx.spring_layout(G, seed=seed + 1234)
        layouts.append(normalize_pos(pos))

    # Pad to exactly n_layouts
    while len(layouts) < n_layouts:
        s = rng.randint(0, 100000)
        k_val = 1.5 / math.sqrt(max(G.number_of_nodes(), 1))
        pos = nx.spring_layout(G, seed=int(s), iterations=300, k=k_val)
        layouts.append(normalize_pos(pos))

    return layouts[:n_layouts]


# ============================================================
# Graph verification
# ============================================================

def verify_graph(G, label="", expected_v=None, expected_e=None, quiet=False):
    """
    Run sanity checks on a graph. Returns True if all checks pass.
    Prints a status line unless quiet=True.
    """
    v = G.number_of_nodes()
    e = G.number_of_edges()
    is_planar, _ = nx.check_planarity(G)
    is_connected = nx.is_connected(G) if v > 0 else False
    is_maximal_planar = (e == 3 * v - 6) if v >= 3 else False

    status = "OK"
    if not is_planar:
        status = "FAIL(non-planar)"
    if not is_connected:
        status = "FAIL(disconnected)"
    if expected_v is not None and v != expected_v:
        status = f"FAIL(V={v}, expected {expected_v})"
    if expected_e is not None and e != expected_e:
        status = f"FAIL(E={e}, expected {expected_e})"

    if not quiet:
        degs = sorted(dict(G.degree()).values()) if v > 0 else [0]
        print(f"  [{status:>20s}] {label:30s}  V={v:3d}  E={e:3d}  "
              f"planar={is_planar}  conn={is_connected}  "
              f"maxplanar={is_maximal_planar}  "
              f"deg=[{min(degs)},{max(degs)}]")

    return status == "OK"


# ============================================================
# Standardized metadata computation
# ============================================================

def compute_standard_metadata(G):
    """
    Compute standardized graph-theory measures.
    Returns a dict to be merged into G.graph.
    Called by the control script, NOT by daughter modules.
    """
    v = G.number_of_nodes()
    e = G.number_of_edges()
    is_planar, _ = nx.check_planarity(G)
    is_connected = nx.is_connected(G) if v > 0 else False

    degrees = [d for _, d in G.degree()]
    degree_seq = sorted(degrees, reverse=True)

    meta = {
        'vertices': v,
        'edges': e,
        'is_planar': is_planar,
        'is_connected': is_connected,
        'degree_sequence': degree_seq,
        'min_degree': min(degrees) if degrees else 0,
        'max_degree': max(degrees) if degrees else 0,
        'avg_degree': sum(degrees) / len(degrees) if degrees else 0.0,
        'density': nx.density(G),
        'is_bipartite': nx.is_bipartite(G),
        'is_tree': nx.is_tree(G),
    }

    # Girth (length of shortest cycle) — can be expensive for large graphs
    if v <= 100:
        try:
            meta['girth'] = nx.girth(G)
        except Exception:
            meta['girth'] = None
    else:
        meta['girth'] = None

    # Chromatic number — exact computation is NP-hard, so we use greedy bound
    # and set exact value only for known cases
    if v == 0:
        meta['chromatic_number_greedy'] = 0
    else:
        try:
            coloring = nx.coloring.greedy_color(G, strategy='largest_first')
            meta['chromatic_number_greedy'] = max(coloring.values()) + 1
        except Exception:
            meta['chromatic_number_greedy'] = None

    return meta
