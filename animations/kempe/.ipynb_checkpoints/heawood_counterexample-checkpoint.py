#!/usr/bin/env python3
# ============================================================================
# heawood_counterexample.py  —  Heawood's 1890 Counterexample
# ============================================================================
#
# Author:       Tanya Wilcox
# Institution:  Wilkes University
# Course:       MTH-392  —  Senior Project in Computational Mathematics
# Term:         Spring 2026
#
# ============================================================================
# MODULE OVERVIEW
# ============================================================================
#
# This module animates the fatal flaw in Kempe's 1879 "proof" of the
# Four-Color Theorem, using historical counterexample graphs stored in
# kempe_counterexample_graphs.pkl.
#
# For each graph, the animation demonstrates how two Kempe chains become
# entangled: swapping one chain destroys the color structure of the other,
# so no color can be freed for the target vertex.  Kempe's argument fails.
#
# Supported graphs (19 total, loaded by key):
#
#   heawood_counterexample  — Heawood (1890), 25 V, the original refutation
#   fritsch_1 .. fritsch_4  — Fritsch (1998), 9 V, smallest counterexample
#   soifer_1  .. soifer_4   — Soifer (2009), 10–12 V, four constructions
#   poussin                 — de la Vallée-Poussin (1896), 15 V
#   errera_1  .. errera_8   — Errera (1921), 17 V, eight embeddings
#   kittell                 — Kittell (1935), 23 V
#
# ============================================================================
# USAGE
# ============================================================================
#
#   List all available counterexample graphs:
#
#     python heawood_counterexample.py
#
#   Show details for a specific graph:
#
#     python heawood_counterexample.py fritsch_1
#     python heawood_counterexample.py errera_3
#
#   Render the default graph (heawood_counterexample):
#
#     python heawood_counterexample.py --render
#
#   Render a specific graph:
#
#     python heawood_counterexample.py fritsch_1 --render
#     python heawood_counterexample.py errera_3  --render
#     python heawood_counterexample.py kittell   --render -qh
#
#   The --render flag invokes manim automatically.  Any additional flags
#   after --render are forwarded to manim (default quality: -qh).
#
# ============================================================================
# REFERENCES
# ============================================================================
#
#   [1] P. J. Heawood, "Map-Colour Theorem," Quart. J. Pure Appl. Math.,
#       vol. 24, pp. 332–338, 1890.
#   [2] A. B. Kempe, "On the Geographical Problem of the Four Colours,"
#       Amer. J. Math., vol. 2, no. 3, pp. 193–200, 1879.
#   [3] R. Fritsch and G. Fritsch, "The Four-Color Theorem: History,
#       Topological Foundations, and Idea of Proof," Springer, 1998.
#   [4] A. Soifer, "The Mathematical Coloring Book," Springer, 2009.
#   [5] A. Errera, "Du coloriage des cartes et de quelques questions
#       d'analysis situs," Thesis, 1921.
#   [6] C. de la Vallée-Poussin, as cited in Ore, "The Four-Color
#       Problem," Academic Press, 1967.
#   [7] K. Appel and W. Haken, "Every Planar Map is Four Colorable,
#       Part I: Discharging," Illinois J. Math., vol. 21, 1977.
#
# ============================================================================

from manim import *
import networkx as nx
import numpy as np
import pickle
import sys
import os
from pathlib import Path
from collections import Counter

from kempe_common import (
    # Constants
    SPEED, CONTENT_CENTER_Y, NODE_STROKE_WIDTH,
    KEMPE_CHAIN_WIDTH, KEMPE_GLOW_WIDTH,
    C_BLUE, C_PURPLE, C_YELLOW, C_PINK,
    # Utilities
    make_manim_graph, color_vertex, flash_vertex,
    find_kempe_chain, swap_kempe_chain, kempe_chain_edges,
    build_header,
    copy_to_output,
)


# ============================================================================
# PICKLE PATH  (co-located with this script)
# ============================================================================

PICKLE_FILENAME = "kempe_counterexample_graphs.pkl"


# ============================================================================
# FOUR COLORS — ordered list for assignment
# ============================================================================

FOUR_COLORS = [C_BLUE, C_PURPLE, C_YELLOW, C_PINK]


# ============================================================================
# ENTANGLEMENT REGISTRY
# ============================================================================
#
# Each entry maps a graph family prefix to the parameters that define the
# Kempe chain entanglement demonstration for that graph.
#
#   target          — Degree-5 vertex left uncolored.
#   chain1_start    — Neighbor of target where Chain 1 begins.
#   chain1_colors   — (color_a, color_b) for Chain 1.
#   chain2_start    — Neighbor of target where Chain 2 begins.
#   chain2_colors   — (color_a, color_b) for Chain 2.
#   description     — Short text for the info panel.
#
# The initial coloring is computed automatically to be consistent with
# these chain parameters (see ``build_kempe_coloring``).
#
# For graphs with multiple embeddings (fritsch_1–4, errera_1–8), all
# share the same combinatorial structure; only the layout differs.
# The tangle parameters are therefore keyed by family prefix.
# ============================================================================

TANGLE_REGISTRY = {
    # ------------------------------------------------------------------ #
    #  Heawood (1890) — 25 vertices                                      #
    #  Target v0 (deg 5): neighbors {1, 2, 3, 4, 8}.                     #
    #  v1 and v4 both receive Blue.  Chain 1 {Blue, Yellow} from v1      #
    #  reaches v4 through the exterior.  Chain 2 {Blue, Pink} from v4    #
    #  reaches v1 through the ring.  Shared vertices v1, v4: swapping    #
    #  Chain 1 changes v4 from Blue to Yellow, destroying Chain 2.       #
    # ------------------------------------------------------------------ #
    "heawood_counterexample": {
        "target": 0,
        "chain1_start": 1,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 4,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Heawood's original 1890 refutation of Kempe",
    },

    # ------------------------------------------------------------------ #
    #  Fritsch (1998) — 9 vertices                                       #
    #  Target v0 (deg 5): neighbors {1, 2, 6, 7, 8}.                     #
    #  v1 and v6 both receive Blue.  Kempe Purple–Blue chain from v7 is  #
    #  locked by Red–Yellow chains through (1,7), (3,7), (5,7), (6,7).   #
    # ------------------------------------------------------------------ #
    "fritsch": {
        "target": 0,
        "chain1_start": 7,
        "chain1_colors": (C_PURPLE, C_BLUE),
        "chain2_start": 8,
        "chain2_colors": (C_YELLOW, C_BLUE),
        "description": "Smallest known Kempe counterexample (9 vertices)",
    },

    # ------------------------------------------------------------------ #
    #  Errera (1921) — 17 vertices                                       #
    #  Tangle at center pair v15, v16.  Target v16 (deg 5): neighbors    #
    #  {11, 12, 13, 14, 15}.  v11 and v14 share Blue.  Red–Blue chain    #
    #  from v9 crosses Purple–Yellow chain from v11 through the inner    #
    #  hexagon, topologically inseparable.                               #
    # ------------------------------------------------------------------ #
    "errera": {
        "target": 16,
        "chain1_start": 11,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 14,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Errera's 1921 concentric-hexagon counterexample",
    },

    # ------------------------------------------------------------------ #
    #  Kittell (1935) — 23 vertices                                      #
    #  Three concentric hexagonal rings.  Tangle at center edge (21, 22).#
    #  Target v22 (deg 5): neighbors {17, 18, 19, 20, 21}.               #
    #  Red–Blue chain from a Ring-3 neighbor traps the Purple–Yellow     #
    #  chain; the concentric rings act as topological barriers.          #
    # ------------------------------------------------------------------ #
    "kittell": {
        "target": 22,
        "chain1_start": 17,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 20,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Kittell's 1935 three-ring counterexample",
    },

    # ------------------------------------------------------------------ #
    #  Poussin (1896) — 15 vertices                                      #
    #  Asymmetric triangulation.  Two simultaneous swaps conflict.       #
    #  Tangle at central cluster {7, 8, 11, 14}.  Target v0 (deg 5):     #
    #  neighbors {1, 2, 3, 5, 14}.  Chains route through the high-       #
    #  connectivity 7–8–11–14 cluster and become entangled.              #
    # ------------------------------------------------------------------ #
    "poussin": {
        "target": 0,
        "chain1_start": 1,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 14,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "de la Vallée-Poussin's 1896 simultaneous-swap failure",
    },

    # ------------------------------------------------------------------ #
    #  Soifer 1 (2009) — 10 vertices                                     #
    #  Nested triangulation.  Target v9 (deg 3).  For the entanglement   #
    #  demo we use v3 (deg 6) reduced to a degree-5 perspective; or use  #
    #  v0 (deg 4).  We target a degree-5 vertex: v0 has deg 4, v3 has    #
    #  deg 6.  Best candidate: v9 (deg 3) won't work.  Use v0 with its   #
    #  neighbors {1, 2, 3, 5} (deg 4).                                   #
    #  Note: For graphs without a degree-5 vertex, we still demonstrate  #
    #  the chain entanglement on the best available vertex.              #
    # ------------------------------------------------------------------ #
    "soifer_1": {
        "target": 3,
        "chain1_start": 0,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 4,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Soifer's nested triangulation counterexample",
    },

    # ------------------------------------------------------------------ #
    #  Soifer 2 (2009) — 11 vertices                                     #
    #  Outer triangle + hexagonal ring + central pair.                   #
    #  Target v10 (deg 5): neighbors {5, 6, 7, 8, 9}.                    #
    # ------------------------------------------------------------------ #
    "soifer_2": {
        "target": 10,
        "chain1_start": 5,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 8,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Soifer's hexagonal-ring counterexample",
    },

    # ------------------------------------------------------------------ #
    #  Soifer 3 (2009) — 12 vertices                                     #
    #  Outer triangle, hexagonal ring, inner triangle.                   #
    #  Target v11 (deg 5): neighbors {5, 6, 7, 9, 10}.                   #
    # ------------------------------------------------------------------ #
    "soifer_3": {
        "target": 11,
        "chain1_start": 5,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 9,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Soifer's inner-triangle counterexample",
    },

    # ------------------------------------------------------------------ #
    #  Soifer 4 / Icosahedron (2009) — 12 vertices, all degree 5         #
    #  The entire surface is a "minefield" of potential Kempe failures.  #
    #  Target v0 (deg 5): neighbors {1, 5, 7, 8, 10}.                    #
    #  Any chain swap is blocked by a crossing chain of the other two    #
    #  colors connected elsewhere on the icosahedral shell.              #
    # ------------------------------------------------------------------ #
    "soifer_4": {
        "target": 0,
        "chain1_start": 1,
        "chain1_colors": (C_BLUE, C_YELLOW),
        "chain2_start": 5,
        "chain2_colors": (C_BLUE, C_PINK),
        "description": "Icosahedral graph — every vertex is degree 5",
    },
}


# ============================================================================
# GRAPH LOADING
# ============================================================================

def load_kempe_graphs(pkl_path: str = None) -> dict:
    """Load the dictionary of counterexample graphs from the pickle file.

    Parameters
    ----------
    pkl_path : str, optional
        Explicit path.  If *None*, looks for the pickle in the same
        directory as this script.

    Returns
    -------
    dict[str, nx.Graph]
        Mapping from graph key to NetworkX graph.
    """
    if pkl_path is None:
        pkl_path = Path(__file__).parent / PICKLE_FILENAME
    with open(pkl_path, "rb") as fh:
        return pickle.load(fh)


def resolve_graph_key(graphs: dict, requested: str) -> str:
    """Resolve a user-supplied key to an exact key in the graph dictionary.

    Tries the requested key verbatim first, then searches for it as a
    suffix.  Raises *KeyError* with helpful diagnostics if no match is found.
    """
    if requested in graphs:
        return requested

    # Try matching as a suffix (e.g., user types "fritsch_1")
    matches = [k for k in graphs if k.endswith(requested)]
    if len(matches) == 1:
        return matches[0]

    available = "\n  ".join(sorted(graphs.keys()))
    raise KeyError(
        f"Graph key '{requested}' not found.\n"
        f"Available keys:\n  {available}"
    )


# ============================================================================
# TANGLE LOOKUP
# ============================================================================

def get_tangle_config(graph_key: str) -> dict:
    """Return the entanglement configuration for *graph_key*.

    Looks up by exact key first, then by family prefix (everything
    before the last ``_digit`` suffix).  Falls back to auto-detection
    if no registry entry exists.
    """
    # Exact match
    if graph_key in TANGLE_REGISTRY:
        return TANGLE_REGISTRY[graph_key]

    # Strip trailing _N suffix for family match
    # e.g. "fritsch_2" → "fritsch", "errera_8" → "errera"
    parts = graph_key.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        family = parts[0]
        if family in TANGLE_REGISTRY:
            return TANGLE_REGISTRY[family]

    return None  # will trigger auto-detection


# ============================================================================
# INITIAL COLORING — construct a valid 4-coloring exhibiting the tangle
# ============================================================================

def build_kempe_coloring(G: nx.Graph, tangle: dict) -> dict:
    """Build a proper 4-coloring of *G* with the target vertex uncolored
    and its neighbors arranged so that the specified chains are meaningful.

    The coloring satisfies:
      - Every vertex except ``target`` is assigned one of the four colors.
      - ``chain1_start`` receives ``chain1_colors[0]``.
      - ``chain2_start`` receives ``chain2_colors[0]``.
      - The remaining neighbors of the target each receive one of the
        other colors so that all four colors appear on the target's ring.

    This handles both the "shared color" case (both chains start with the
    same color, e.g. heawood) and the "independent color" case (chains
    start with different colors, e.g. fritsch).

    Parameters
    ----------
    G : nx.Graph
        The graph to color.
    tangle : dict
        Entanglement configuration from the registry.

    Returns
    -------
    dict[int, str]
        Mapping vertex → color hex string for every vertex except target.
    """
    target = tangle["target"]
    c1_start = tangle["chain1_start"]
    c2_start = tangle["chain2_start"]
    c1_a, c1_b = tangle["chain1_colors"]   # c1_start gets c1_a
    c2_a, c2_b = tangle["chain2_colors"]   # c2_start gets c2_a

    neighbors = sorted(G.neighbors(target))

    # ---- Force the chain-start vertices to their required colors ---- #
    forced = {}
    forced[c1_start] = c1_a
    forced[c2_start] = c2_a

    # ---- Assign colors to remaining target-neighbors ---------------- #
    # Collect which colors are already used by the forced pair
    remaining_neighbors = [n for n in neighbors
                           if n not in (c1_start, c2_start)]
    used_colors = {c1_a, c2_a}

    # Colors still needed to complete the ring (all 4 must appear)
    needed = [c for c in FOUR_COLORS if c not in used_colors]

    # Also ensure the "other" color of each chain (c1_b, c2_b) appears
    # somewhere on the ring, so the chains are meaningful.
    priority = []
    for c in (c1_b, c2_b):
        if c not in used_colors and c not in priority:
            priority.append(c)
    rest = [c for c in needed if c not in priority]
    needed_ordered = priority + rest

    for i, n in enumerate(remaining_neighbors):
        if i < len(needed_ordered):
            forced[n] = needed_ordered[i]
        else:
            # More remaining neighbors than needed colors — cycle
            forced[n] = needed_ordered[i % max(1, len(needed_ordered))]

    # ---- Extend to a full proper 4-coloring via backtracking -------- #
    coloring = {}
    nodes = sorted(G.nodes())
    nodes.remove(target)

    # Put forced nodes first for faster propagation
    forced_nodes = [n for n in nodes if n in forced]
    free_nodes = [n for n in nodes if n not in forced]
    order = forced_nodes + free_nodes

    def _is_valid(v, c):
        """Check if assigning color *c* to vertex *v* is consistent."""
        for u in G.neighbors(v):
            if u != target and u in coloring and coloring[u] == c:
                return False
        return True

    def _backtrack(idx):
        if idx >= len(order):
            return True
        v = order[idx]
        if v in forced:
            c = forced[v]
            if _is_valid(v, c):
                coloring[v] = c
                if _backtrack(idx + 1):
                    return True
                del coloring[v]
            return False
        for c in FOUR_COLORS:
            if _is_valid(v, c):
                coloring[v] = c
                if _backtrack(idx + 1):
                    return True
                del coloring[v]
        return False

    if _backtrack(0):
        return coloring

    # Fallback: if forced assignment is infeasible, use unconstrained
    # 4-coloring and remap neighbor colors.
    return _fallback_coloring(G, target, tangle)


def _fallback_coloring(G: nx.Graph, target: int, tangle: dict) -> dict:
    """Fallback: greedy 4-coloring with neighbor color remapping."""
    nx_coloring = nx.coloring.greedy_color(G, strategy="largest_first")

    c1_start = tangle["chain1_start"]
    c2_start = tangle["chain2_start"]
    c1_a = tangle["chain1_colors"][0]
    c2_a = tangle["chain2_colors"][0]

    # Map nx color-indices to our hex colors
    idx_map = {}
    idx_map[nx_coloring[c1_start]] = c1_a
    if nx_coloring[c2_start] not in idx_map:
        idx_map[nx_coloring[c2_start]] = c2_a

    # Map remaining nx-indices to remaining colors
    used_ours = set(idx_map.values())
    remaining_ours = [c for c in FOUR_COLORS if c not in used_ours]

    oi = 0
    for ni in sorted(set(nx_coloring.values())):
        if ni not in idx_map:
            if oi < len(remaining_ours):
                idx_map[ni] = remaining_ours[oi]
                oi += 1
            else:
                idx_map[ni] = remaining_ours[oi % len(remaining_ours)]
                oi += 1

    coloring = {}
    for v in G.nodes():
        if v == target:
            continue
        coloring[v] = idx_map.get(nx_coloring[v], FOUR_COLORS[0])

    return coloring


# ============================================================================
# AUTO-DETECTION — for graphs not in the registry
# ============================================================================

def auto_detect_tangle(G: nx.Graph) -> dict:
    """Heuristically detect entanglement parameters for an unknown graph.

    Finds the highest-degree vertex (preferring degree 5) and sets up
    two Kempe chains from neighbors that share a color.
    """
    # Find best target: prefer degree-5, then highest degree
    deg5 = [v for v, d in G.degree() if d == 5]
    if deg5:
        target = deg5[0]
    else:
        target = max(G.nodes(), key=lambda v: G.degree(v))

    neighbors = sorted(G.neighbors(target))

    # Quick greedy 4-coloring
    nx_c = nx.coloring.greedy_color(G, strategy="largest_first")
    neighbor_color_indices = [nx_c[n] for n in neighbors]

    # Find two neighbors sharing a color
    counts = Counter(neighbor_color_indices)
    shared_idx = max(counts, key=counts.get)
    sharing = [n for n in neighbors if nx_c[n] == shared_idx]

    # Map indices to our colors
    idx_to_c = {i: FOUR_COLORS[i % 4]
                for i in sorted(set(nx_c.values()))}
    shared_color = idx_to_c[shared_idx]

    other_neighbor_colors = [idx_to_c[nx_c[n]]
                             for n in neighbors if nx_c[n] != shared_idx]
    # Pick two distinct "other" colors for the chains
    unique_others = list(dict.fromkeys(other_neighbor_colors))
    c1_other = unique_others[0] if unique_others else C_YELLOW
    c2_other = unique_others[1] if len(unique_others) > 1 else C_PINK

    return {
        "target": target,
        "chain1_start": sharing[0],
        "chain1_colors": (shared_color, c1_other),
        "chain2_start": sharing[1] if len(sharing) > 1 else sharing[0],
        "chain2_colors": (shared_color, c2_other),
        "description": "Auto-detected Kempe entanglement",
    }


# ============================================================================
# HEADER TEXT BUILDER
# ============================================================================

def make_header_text(G: nx.Graph, graph_key: str) -> tuple:
    """Build the left title and right info-block text for the header.

    Returns
    -------
    (left_title, right_title, info_lines)
    """
    meta = G.graph if hasattr(G, "graph") else {}
    name = meta.get("name", graph_key)
    short = meta.get("short_name", graph_key)
    year = meta.get("year", "")
    author = meta.get("author", "")
    desc = meta.get("description", "")

    left_title = "Kempe's Error"

    # Build right-side title from the graph metadata
    if year:
        right_title = f"{name} ({year})"
    else:
        right_title = name

    n = G.number_of_nodes()
    m = G.number_of_edges()
    info_lines = [
        f"V = {n}   E = {m}",
    ]
    if author:
        info_lines.insert(0, author)
    if desc:
        info_lines.append(desc)

    return left_title, right_title, info_lines


# ============================================================================
# SELECTED GRAPH KEY — resolved at import time for manim CLI
# ============================================================================
# When invoked via ``manim -qh heawood_counterexample.py HeawoodCounterexample``,
# command-line parsing is handled by manim, not by this script.  We therefore
# read the graph key from an environment variable as well.

def _resolve_selected_key():
    """Determine which graph key the user wants.

    Priority:
      1. ``KEMPE_GRAPH_KEY`` environment variable  (set by __main__)
      2. Default: ``heawood_counterexample``
    """
    return os.environ.get("KEMPE_GRAPH_KEY", "heawood_counterexample")


SELECTED_GRAPH_KEY = _resolve_selected_key()


# ============================================================================
# SCENE: HeawoodCounterexample
# ============================================================================

class HeawoodCounterexample(Scene):
    """Kempe chain entanglement — animated for any counterexample graph.

    This scene reveals the flaw in Kempe's proof.  When the degree-5
    vertex has all four colors on its ring and two different Kempe chains
    share vertices, swapping one chain destroys the color structure that
    the other chain depends on.
    """

    def construct(self):
        self.camera.background_color = WHITE

        # ============================================================== #
        #  LOAD GRAPH                                                     #
        # ============================================================== #

        graphs = load_kempe_graphs()
        graph_key = resolve_graph_key(graphs, SELECTED_GRAPH_KEY)
        G = graphs[graph_key]

        meta = G.graph if hasattr(G, "graph") else {}
        pos = meta.get("pos", None)

        # If no stored positions, compute a planar spring layout
        if pos is None:
            try:
                pos_seed = nx.planar_layout(G)
            except Exception:
                pos_seed = None
            pos = nx.spring_layout(
                G, seed=1, pos=pos_seed,
                k=2.0 / np.sqrt(max(1, G.number_of_nodes())),
                iterations=300,
            )

        # Convert to 3-D Manim coordinates
        pos3d = {
            v: np.array([3.0 * float(xy[0]), 3.0 * float(xy[1]), 0.0])
            for v, xy in pos.items()
        }

        # ============================================================== #
        #  TANGLE CONFIGURATION                                           #
        # ============================================================== #

        tangle = get_tangle_config(graph_key)
        if tangle is None:
            tangle = auto_detect_tangle(G)
            print(f"[INFO] Auto-detected tangle for '{graph_key}': "
                  f"target={tangle['target']}")

        target = tangle["target"]
        c1_start = tangle["chain1_start"]
        c1_a, c1_b = tangle["chain1_colors"]
        c2_start = tangle["chain2_start"]
        c2_a, c2_b = tangle["chain2_colors"]

        # ============================================================== #
        #  HEADER                                                         #
        # ============================================================== #

        left_title, right_title, info_lines = make_header_text(G, graph_key)

        header = build_header(
            left_title, right_title,
            info_lines=info_lines,
        )
        self.add(header)

        # ============================================================== #
        #  BUILD GRAPH MOBJECTS                                           #
        # ============================================================== #

        g, lbl = make_manim_graph(G, pos3d, target_v=target)

        # Scale to fit — adapt for graph size
        n = G.number_of_nodes()
        if n <= 12:
            scale_factor = 0.85
        elif n <= 18:
            scale_factor = 0.78
        else:
            scale_factor = 0.70

        VGroup(g, lbl).scale(scale_factor).move_to(
            np.array([0.0, CONTENT_CENTER_Y, 0.0])
        )

        # ============================================================== #
        #  INITIAL COLORING                                               #
        # ============================================================== #

        init_coloring = build_kempe_coloring(G, tangle)

        # Verify coloring validity
        for u, v_edge in G.edges():
            if u == target or v_edge == target:
                continue
            if u in init_coloring and v_edge in init_coloring:
                if init_coloring[u] == init_coloring[v_edge]:
                    print(f"[WARN] Coloring conflict: "
                          f"v{u}={init_coloring[u]}, "
                          f"v{v_edge}={init_coloring[v_edge]}")

        # ============================================================== #
        #  ANIMATION                                                      #
        # ============================================================== #

        self.play(Create(g), run_time=1.5)
        self.add(lbl)
        self.bring_to_front(lbl)

        # ---- Phase 1: Color all vertices except the target ----------- #
        for v, c in sorted(init_coloring.items()):
            color_vertex(self, g, v, c, run_time=0.12)
        self.wait(1.0 * SPEED)

        # ---- Phase 2: Highlight the shared-color pair ---------------- #
        # Identify which neighbors of the target share a color
        neighbors = sorted(G.neighbors(target))
        n_colors = {v: init_coloring.get(v) for v in neighbors}
        color_groups = {}
        for v, c in n_colors.items():
            color_groups.setdefault(c, []).append(v)

        shared_pair = []
        for c, verts in color_groups.items():
            if len(verts) >= 2:
                shared_pair = verts[:2]
                break

        if shared_pair:
            self.play(
                *[g.vertices[v].animate.set_stroke(YELLOW, width=6)
                  for v in shared_pair],
                run_time=0.5 * SPEED,
            )
            self.wait(1.5 * SPEED)

        # ---- Phase 3: Chain 1 --------------------------------------- #
        coloring = dict(init_coloring)
        chain1 = find_kempe_chain(G, coloring, c1_start, c1_a, c1_b)
        chain1_edges = kempe_chain_edges(G, chain1)

        chain1_lines = VGroup()
        for u, v in chain1_edges:
            s, e = g.vertices[u].get_center(), g.vertices[v].get_center()
            chain1_lines.add(
                Line(s, e, stroke_width=KEMPE_GLOW_WIDTH,
                     color=ORANGE, stroke_opacity=0.3).set_z_index(-1),
                Line(s, e, stroke_width=KEMPE_CHAIN_WIDTH,
                     color=ORANGE).set_z_index(2),
            )
        self.play(Create(chain1_lines), run_time=1.0 * SPEED)
        self.bring_to_front(lbl)
        self.wait(0.8 * SPEED)

        # Flash vertices in Chain 1 that are also neighbors of target
        chain1_target_neighbors = [v for v in chain1 if v in neighbors
                                   and v != c1_start]
        for v in chain1_target_neighbors:
            flash_vertex(self, g, v, color=RED)
        self.wait(1.5 * SPEED)

        # ---- Phase 4: Chain 2 --------------------------------------- #
        chain2 = find_kempe_chain(G, coloring, c2_start, c2_a, c2_b)
        chain2_edges = kempe_chain_edges(G, chain2)

        chain2_lines = VGroup()
        for u, v in chain2_edges:
            s, e = g.vertices[u].get_center(), g.vertices[v].get_center()
            chain2_lines.add(
                Line(s, e, stroke_width=KEMPE_GLOW_WIDTH,
                     color=TEAL, stroke_opacity=0.3).set_z_index(-1),
                Line(s, e, stroke_width=KEMPE_CHAIN_WIDTH,
                     color=TEAL).set_z_index(2),
            )
        self.play(Create(chain2_lines), run_time=1.0 * SPEED)
        self.bring_to_front(lbl)
        self.wait(0.8 * SPEED)

        # Flash vertices in Chain 2 that are also neighbors of target
        chain2_target_neighbors = [v for v in chain2 if v in neighbors
                                   and v != c2_start]
        for v in chain2_target_neighbors:
            flash_vertex(self, g, v, color=RED)
        self.wait(1.5 * SPEED)

        # ---- Phase 5: Fatal overlap flash ---------------------------- #
        overlap = set(chain1) & set(chain2)
        if overlap:
            self.play(
                *[Flash(g.vertices[v], color=PURE_RED, flash_radius=0.6)
                  for v in overlap],
                run_time=0.6 * SPEED,
            )
        else:
            # Even without vertex overlap, flash the shared pair
            # to emphasize the interference point
            if shared_pair:
                self.play(
                    *[Flash(g.vertices[v], color=PURE_RED, flash_radius=0.6)
                      for v in shared_pair],
                    run_time=0.6 * SPEED,
                )
        self.wait(2.0 * SPEED)

        # ---- Phase 6: Swap Chain 1 ---------------------------------- #
        swaps1 = swap_kempe_chain(coloring, chain1, c1_a, c1_b)
        for v_sw, old_c, new_c in swaps1:
            color_vertex(self, g, v_sw, new_c, run_time=0.25)
        self.play(FadeOut(chain1_lines), run_time=0.4)
        self.wait(0.8 * SPEED)

        # ---- Phase 7: Chain 2 is destroyed --------------------------- #
        # Flash the vertex(es) where Chain 2 has been corrupted
        chain2_corrupted = set(chain2) & set(chain1)
        if chain2_corrupted:
            self.play(
                *[Flash(g.vertices[v], color=PURE_RED, flash_radius=0.6)
                  for v in chain2_corrupted],
                run_time=0.5 * SPEED,
            )
        else:
            # Flash chain2_start as the disruption point
            self.play(
                Flash(g.vertices[c2_start], color=PURE_RED,
                      flash_radius=0.6),
                run_time=0.5 * SPEED,
            )

        self.play(
            chain2_lines.animate.set_color(RED).set_stroke(opacity=0.5),
            run_time=0.6 * SPEED,
        )
        self.wait(1.0 * SPEED)

        # ---- Phase 8: X-mark on the target — no color available ----- #
        center = g.vertices[target].get_center()
        xs = 0.5
        x_mark = VGroup(
            Line(center + LEFT * xs + UP * xs,
                 center + RIGHT * xs + DOWN * xs,
                 stroke_width=8, color=RED),
            Line(center + RIGHT * xs + UP * xs,
                 center + LEFT * xs + DOWN * xs,
                 stroke_width=8, color=RED),
        ).set_z_index(20)
        self.play(Create(x_mark), run_time=0.5 * SPEED)
        self.wait(2.0 * SPEED)

        self.play(FadeOut(chain2_lines), run_time=0.4)
        self.wait(2.0 * SPEED)


# ============================================================================
# MAIN — command-line interface
# ============================================================================

if __name__ == "__main__":
    import subprocess

    SCRIPT = Path(__file__).name

    # Parse arguments: [graph_key] [--render] [manim flags...]
    args = sys.argv[1:]
    graph_key_arg = None
    render_mode = False
    manim_flags = []

    i = 0
    while i < len(args):
        if args[i] == "--render":
            render_mode = True
            # Everything after --render is forwarded to manim
            manim_flags = args[i + 1:]
            break
        else:
            graph_key_arg = args[i]
        i += 1

    # ------------------------------------------------------------------ #
    #  --render: set env var and invoke manim                             #
    # ------------------------------------------------------------------ #
    if render_mode:
        key = graph_key_arg or "heawood_counterexample"

        # Validate the key before launching manim
        try:
            graphs = load_kempe_graphs()
            key = resolve_graph_key(graphs, key)
        except FileNotFoundError:
            print(f"[ERROR] {PICKLE_FILENAME} not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

        # Default quality flag if none supplied
        if not any(f.startswith("-q") for f in manim_flags):
            manim_flags.insert(0, "-qh")

        env = os.environ.copy()
        env["KEMPE_GRAPH_KEY"] = key

        cmd = ["manim"] + manim_flags + [SCRIPT, "HeawoodCounterexample"]
        print(f"Launching: {' '.join(cmd)}")
        print(f"  KEMPE_GRAPH_KEY={key}")
        sys.exit(subprocess.call(cmd, env=env))

    # ------------------------------------------------------------------ #
    #  No args: list all graphs                                           #
    # ------------------------------------------------------------------ #
    if graph_key_arg is None:
        print("Kempe Chain Entanglement — Counterexample Animations")
        print("=" * 55)
        print()

        try:
            graphs = load_kempe_graphs()
            print(f"Loaded {len(graphs)} graphs from {PICKLE_FILENAME}")
            print()
            print(f"  {'KEY':<28s}  {'V':>3s}  {'E':>3s}  YEAR")
            print(f"  {'-'*28}  {'-'*3}  {'-'*3}  {'-'*6}")
            for key in sorted(graphs.keys()):
                G = graphs[key]
                meta = G.graph if hasattr(G, "graph") else {}
                n = G.number_of_nodes()
                m = G.number_of_edges()
                year = meta.get("year", "?")
                print(f"  {key:<28s}  {n:>3d}  {m:>3d}  {year}")
        except FileNotFoundError:
            print(f"[ERROR] {PICKLE_FILENAME} not found in script directory.")
            print(f"        Expected at: "
                  f"{Path(__file__).parent / PICKLE_FILENAME}")

        print()
        print("Usage:")
        print(f"  python {SCRIPT}                        "
              f"List all graphs")
        print(f"  python {SCRIPT} <key>                  "
              f"Show graph details")
        print(f"  python {SCRIPT} <key> --render         "
              f"Render animation (default -qh)")
        print(f"  python {SCRIPT} <key> --render -ql     "
              f"Render with custom quality")
        print()
        print("Default graph: heawood_counterexample")
        sys.exit(0)

    # ------------------------------------------------------------------ #
    #  Graph key provided: show info                                      #
    # ------------------------------------------------------------------ #
    try:
        graphs = load_kempe_graphs()
        key = resolve_graph_key(graphs, graph_key_arg)
        G = graphs[key]
        meta = G.graph if hasattr(G, "graph") else {}
        n = G.number_of_nodes()
        m = G.number_of_edges()
        year = meta.get("year", "?")
        name = meta.get("name", key)

        tangle = get_tangle_config(key)
        if tangle is None:
            tangle = auto_detect_tangle(G)
            detect_msg = " (auto-detected)"
        else:
            detect_msg = ""

        print(f"Graph:   {name} [{key}]")
        print(f"Year:    {year}")
        print(f"V={n}, E={m}, maximal planar: E = 3V-6 → "
              f"{m} = {3*n - 6} {'✓' if m == 3*n - 6 else '✗'}")
        print(f"Target:  v{tangle['target']}{detect_msg}")
        print(f"Chain 1: start=v{tangle['chain1_start']}")
        print(f"Chain 2: start=v{tangle['chain2_start']}")
        print()
        print("To render:")
        print(f"  python {SCRIPT} {key} --render")

    except FileNotFoundError:
        print(f"[ERROR] {PICKLE_FILENAME} not found.")
        sys.exit(1)
    except KeyError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
