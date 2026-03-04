#!/usr/bin/env python3
# ============================================================================
# coloring_animation.py
# ============================================================================
#
# Author:       Tanya Wilcox
# Institution:  Wilkes University
# Course:       MTH-392  —  Senior Project in Computational Mathematics
# Term:         Spring 2026
#
# ============================================================================
# PROJECT OVERVIEW
# ============================================================================
#
# This script is one component of a larger senior-project investigation of
# the Four-Color Theorem (4CT).  The 4CT states that the regions of every
# planar map can be colored with at most four colors so that no two adjacent
# regions share the same color.  Equivalently, every planar graph is
# 4-vertex-colorable.
#
# The theorem was first proved by Appel and Haken (1977) using an unavoidable
# set of 1,834 reducible configurations (later trimmed to 1,482).  Robertson,
# Sanders, Seymour, and Thomas (1997) gave a simplified proof using 633
# configurations whose reducibility was verified by computer.  Gonthier
# (2008) formalized the entire argument in the Coq proof assistant.
#
# This script creates an animated prologue that illustrates the primal-to-dual
# transformation central to the Four-Color Theorem.  As Gonthier (2008)
# notes, "the first step in the proof consists precisely in getting rid of
# the topology, reducing an infinite problem in analysis to a finite problem
# in combinatorics.  This is usually done by constructing the dual graph of
# the map."
#
# This script animates how different graph-coloring heuristics assign colors
# to graphs from the planar graph library (all_planar_graphs.pkl).  Currently
# the library contains 633 RSST unavoidable configurations and 19 Kempe
# counterexample graphs, with more modules planned.  It uses the Manim
# library to render step-by-step videos that show vertex selection, color
# assignment, conflict detection, and backtracking.  A heads-up display
# (HUD) overlays real-time statistics, and a three-panel header reports
# the graph's identity, its Euler-formula verification (V - E + F = 2),
# and its degree statistics.
#
# The prologue proceeds in four phases:
#
#   Phase 1 — THE MAP:  Voronoi cells (computed from vertex positions) are
#             rendered as colored polygonal regions, forming a "primal map."
#             Each region's color corresponds to the algorithm's final
#             4-color assignment for that vertex.
#
#   Phase 2 — THE TRANSITION:  Each Voronoi cell "melts" — shrinking toward
#             its center point — while graph vertices grow at those centers
#             and dual edges fade in between adjacent vertices.
#
#   Phase 3 — COLOR PERSISTENCE:  The graph is now visible with vertices
#             still carrying the same colors as their former regions,
#             demonstrating that coloring vertices IS coloring the map.
#
#   Phase 4 — RESET:  Vertex colors fade to white, returning the graph to
#             its uncolored state, ready for the step-by-step algorithm
#             animation to begin.
#
# The Voronoi cells are clipped to the full usable graph area so the entire
# center of the frame is tiled with the colored map.  This works generically
# for all planar graphs in the library.
#
# ============================================================================
# WHAT THIS SCRIPT PRODUCES
# ============================================================================
#
#   1.  An MP4 video of the duality prologue followed by the coloring
#       animation (saved to VIDEO_OUTPUT_DIR).
#   2.  A JSON metadata file recording graph properties, algorithm choice,
#       and run statistics (saved to JSON_OUTPUT_DIR).
#   3.  A row appended to a cumulative CSV leaderboard that tracks every run,
#       enabling cross-algorithm comparison (saved to LEADERBOARD_DIR).
#
# ============================================================================
# USAGE
# ============================================================================
#
#   python coloring_animation.py <GRAPH_KEY> <ALGO_NAME> [seed] [--force]
#
#   Arguments
#   ---------
#   GRAPH_KEY  : String key identifying a graph in the library, e.g.:
#                    RSST_001        — RSST unavoidable configuration #1
#                    kempe_fritsch_1 — Fritsch graph (planar embedding)
#                    kempe_errera_3  — Errera graph (3rd layout)
#   ALGO_NAME  : Name of the coloring heuristic.  One of:
#                    Greedy  — Largest-first ordering with backtracking.
#                    DSATUR  — Saturation-degree heuristic (Brelaz, 1979);
#                              falls back to backtracking if >4 colors needed.
#                    SmlLst  — Smallest-last ordering with backtracking.
#                    Random  — Uniformly random vertex ordering; pure greedy
#                              (no backtracking, may use >4 colors).
#   seed       : (Optional, Random only) Integer seed for reproducibility.
#   --force    : Override the animation safety gate.  The algorithm is run
#                first and the total event count is reported.  If the count
#                exceeds MAX_ANIMATION_EVENTS the render is refused unless
#                --force is present.  Can appear anywhere in the argument list.
#
#   Examples
#   --------
#   python coloring_animation.py kempe_fritsch_1 DSATUR
#   python coloring_animation.py RSST_042 Greedy
#   python coloring_animation.py kempe_errera_1 SmlLst
#   python coloring_animation.py RSST_001 Random 42
#
#   Listing Available Graphs
#   ------------------------
#   python coloring_animation.py --list
#   python coloring_animation.py --list kempe
#   python coloring_animation.py --list RSST
#
# ============================================================================
# DEPENDENCIES
# ============================================================================
#
#   - Python 3.10+
#   - Manim Community Edition (manimce)
#   - NetworkX
#   - NumPy
#   - SciPy  (for Voronoi tessellation in the duality prologue)
#
# ============================================================================
# REFERENCES
# ============================================================================
#
#   [1] K. Appel and W. Haken, "Every Planar Map is Four Colorable,"
#       Illinois J. Math., Parts I & II, 1977.
#   [2] N. Robertson, D. Sanders, P. Seymour, and R. Thomas, "The Four-
#       Colour Theorem," J. Combin. Theory Ser. B, vol. 70, pp. 2-44, 1997.
#   [3] N. Robertson, D. Sanders, P. Seymour, and R. Thomas, "Reducibility
#       in the Four-Color Theorem," unpublished manuscript, 1997.
#   [4] G. Gonthier, "Formal Proof -- The Four Color Theorem," Notices of
#       the AMS, vol. 55, no. 11, pp. 1382-1393, 2008.
#   [5] D. Brelaz, "New Methods to Color the Vertices of a Graph," Commun.
#       ACM, vol. 22, no. 4, pp. 251-256, 1979.
#
# ============================================================================

from manim import *
import networkx as nx
import numpy as np
import pickle
import json
import csv
import os
import sys
import shutil
import time
from pathlib import Path
from datetime import datetime

try:
    from scipy.spatial import Voronoi as ScipyVoronoi
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[WARN] scipy not found — duality prologue will be skipped.")


# ============================================================================
# FILE PATHS — imported from centralized config.py
# ============================================================================

# Allow running from any directory by adding project root to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
try:
    from config import (
        ALL_PLANAR_GRAPHS_PKL, VIDEO_CREATED_DIR, VIDEO_JSON_DIR,
        MANIM_MEDIA_DIR as _MANIM_MEDIA_DIR, LEADERBOARD_DIR,
    )
    GRAPHS_PKL_PATH  = str(ALL_PLANAR_GRAPHS_PKL)
    VIDEO_OUTPUT_DIR = str(VIDEO_CREATED_DIR)
    JSON_OUTPUT_DIR  = str(VIDEO_JSON_DIR)
    MANIM_MEDIA_DIR  = str(_MANIM_MEDIA_DIR)
    LEADERBOARD_DIR  = str(LEADERBOARD_DIR)
except ImportError:
    # Fallback: use the original hardcoded paths if config is unavailable.
    import os
    _media_suffix = os.environ.get("MANIM_MEDIA", "")
    GRAPHS_PKL_PATH = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\graph_library\output\all_planar_graphs.pkl"
    )
    VIDEO_OUTPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\Created Videos"
    )
    JSON_OUTPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\JSON Files"
    )
    MANIM_MEDIA_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output"
        + (rf"\worker_{_media_suffix}" if _media_suffix else "")
    )
    LEADERBOARD_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code"
    )


# ============================================================================
# RENDER SETTINGS
# ============================================================================

PIXEL_WIDTH  = 1280
PIXEL_HEIGHT = 1280
FRAME_RATE   = 15
FRAME_HEIGHT = 8.0
FRAME_WIDTH  = FRAME_HEIGHT * (PIXEL_WIDTH / PIXEL_HEIGHT)  # 8.0 for 1:1


# ============================================================================
# VISUAL STYLE CONSTANTS
# ============================================================================

PASTEL_HEX_COLORS = [
    "#8AAFFF", "#D5B1FF", "#FFDA8A", "#FF8AAF",   # colors 0-3 (the four)
    "#DA8AFF", "#AFFF8A", "#9F8AFF", "#FF8AEA",   # colors 4-7  (overflow)
    "#C7D6FF", "#F0C7FF", "#FFF0C7", "#D6FFC7",   # colors 8-11
    "#EBB8FF", "#FFB8CC", "#CCFFB8", "#B8FFEB",   # colors 12-15
    "#B8FFE0", "#BDB8FF", "#FFB8D7", "#FAFFB8",   # colors 16-19
    "#FFB8FB", "#FFDFB8", "#B8FFBC", "#B8D8FF",   # colors 20-23
]

EDGE_COLOR        = BLACK
NODE_STROKE_WIDTH = 3

# --- Auto-sized parameters (computed per-graph) ----------------------------
# These defaults are used ONLY as fallbacks if auto-sizing somehow fails.
# The actual values are computed by compute_visual_params() at render time
# based on the scaled layout geometry (minimum neighbor distance, vertex
# count, and edge density).  See that function's docstring for details.
DEFAULT_NODE_RADIUS       = 0.30
DEFAULT_EDGE_STROKE_WIDTH = 5
DEFAULT_LABEL_FONT_SIZE   = 22


# ============================================================================
# HEADER — "SCENE CARD" LAYOUT
# ============================================================================
# The header is a fixed-height bar at the top of the frame with two zones:
#
#   ┌──────────────┬──────────┬──────────┬──────────┬──────────┐
#   │  Dark Badge  │  V_num   │  E_num   │  F_num   │  Result  │
#   │  MODULE TAG  │ VERTICES │  EDGES   │  FACES   │ EULER ✓  │new_manim_scene
#   └──────────────┴──────────┴──────────┴──────────┴──────────┘
#
# The stat cells spell out the Euler formula: V − E + F = 2.
# Operators (−, +, =) sit on the vertical separator lines.
# ============================================================================

# Font used for numbers, labels, operators in the header and HUD.
# "Consolas" is a clean geometric mono font available on all platforms.
# Change to "Bahnschrift" on Windows 10+ for an exact match to the mockup.
HEADER_FONT = "Consolas"

# Header zone sizes (Manim units)
HEADER_NUM_FONT_SIZE    = 38   # Large V, E, F, result numbers
HEADER_LABEL_FONT_SIZE  = 12   # Small "VERTICES", "EDGES", etc.
HEADER_OP_FONT_SIZE     = 30   # Operator symbols (−, +, =)
BADGE_NAME_FONT_SIZE    = 22   # Graph name inside dark badge
BADGE_MODULE_FONT_SIZE  = 10   # Module subtitle inside dark badge
EULER_CHECK_FONT_SIZE   = 22   # The "✓" or "✗" in the result cell

# Footer / HUD
HUD_FONT_SIZE           = 17
HUD_ALGO_FONT_SIZE      = 15

# Module display name mapping — maps internal module IDs to short labels
# shown in the dark badge.  Add new daughter modules here.
MODULE_DISPLAY_NAMES = {
    "kempe_counterexample": "KEMPE COUNTER",
    "rsst_unavoidable":     "UNAVOIDABLE SET",
}


# ============================================================================
# FIXED LAYOUT MEASUREMENTS (Manim units)
# ============================================================================
#
# The frame is 8.0 × 8.0 (1280 × 1280 px).  All three horizontal bands
# (header, graph area, footer) have FIXED heights so the usable graph
# region is a known, unchanging rectangle.
#
#   ┌────────────────────────────────┐  ← +4.00  (frame top)
#   │  edge_buff = 0.15              │
#   ├────────────────────────────────┤  ← +3.85  (header top)
#   │          HEADER  (1.05)        │
#   ├════════════════════════════════┤  ← +2.80  (header rule)
#   │  gap = 0.10                    │
#   ┌┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┐  ← +2.70  (graph_border top)
#   ┆  inset = 0.10                  ┆
#   ┆  ┌─────────────────────────┐   ┆  ← +2.60  (content top)
#   ┆  │                         │   ┆
#   ┆  │    GRAPH CONTENT AREA   │   ┆
#   ┆  │    7.50 wide × 5.75 tall│   ┆
#   ┆  │                         │   ┆
#   ┆  └─────────────────────────┘   ┆  ← −3.15  (content bottom)
#   ┆  inset = 0.10                  ┆
#   └┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘  ← −3.25  (graph_border bottom)
#   │  gap = 0.10                    │
#   ├════════════════════════════════┤  ← −3.35  (footer rule)
#   │          FOOTER  (0.50)        │
#   ├────────────────────────────────┤  ← −3.85  (footer bottom)
#   │  edge_buff = 0.15              │
#   └────────────────────────────────┘  ← −4.00  (frame bottom)
#
# GRAPH BORDER:          7.70 wide × 5.95 tall  (the visible border rect)
# GRAPH CONTENT AREA:    7.50 wide × 5.75 tall  (where vertices actually go)
#   (that is, x ∈ [−3.75, +3.75],  y ∈ [−3.15, +2.60])
# ============================================================================

EDGE_BUFF           = 0.15
HEADER_HEIGHT       = 1.05     # total height of the header bar
FOOTER_HEIGHT       = 0.50     # total height of the HUD footer bar
HEADER_FOOTER_GAP   = 0.10     # breathing room between rule and graph border
GRAPH_INSET         = 0.10     # padding inside the graph border rectangle
BADGE_WIDTH_FRAC    = 0.20     # badge takes 20% of header width

# Derived constants (computed once from the frame geometry)
_FW = 8.0   # frame width  (must match FRAME_WIDTH)
_FH = 8.0   # frame height (must match FRAME_HEIGHT)

HEADER_TOP    = _FH / 2 - EDGE_BUFF                        # +3.85
HEADER_BOT    = HEADER_TOP - HEADER_HEIGHT                  # +2.80
FOOTER_BOT    = -_FH / 2 + EDGE_BUFF                       # -3.85
FOOTER_TOP    = FOOTER_BOT + FOOTER_HEIGHT                  # -3.35

# Graph border rectangle (the visible thin black line)
GRAPH_Y_MAX   = HEADER_BOT - HEADER_FOOTER_GAP             # +2.70
GRAPH_Y_MIN   = FOOTER_TOP + HEADER_FOOTER_GAP             # -3.25
GRAPH_X_MIN   = -_FW / 2 + EDGE_BUFF                       # -3.85
GRAPH_X_MAX   =  _FW / 2 - EDGE_BUFF                       # +3.85
BORDER_W      = GRAPH_X_MAX - GRAPH_X_MIN                  #  7.70
BORDER_H      = GRAPH_Y_MAX - GRAPH_Y_MIN                  #  5.95

# Actual content area for graph vertices (inset inside the border)
CONTENT_X_MIN = GRAPH_X_MIN + GRAPH_INSET                   # -3.75
CONTENT_X_MAX = GRAPH_X_MAX - GRAPH_INSET                   # +3.75
CONTENT_Y_MIN = GRAPH_Y_MIN + GRAPH_INSET                   # -3.15
CONTENT_Y_MAX = GRAPH_Y_MAX - GRAPH_INSET                   # +2.60
USABLE_W      = CONTENT_X_MAX - CONTENT_X_MIN               #  7.50
USABLE_H      = CONTENT_Y_MAX - CONTENT_Y_MIN               #  5.75

SPRING_K_MULT = 2.0
SPRING_ITERS  = 300

SPEED_FACTOR = 3.0


# ============================================================================
# ANIMATION SAFETY GATE
# ============================================================================
# Maximum number of algorithm events (color + uncolor + conflict) before the
# script refuses to render.  Backtracking on dense triangulations can produce
# tens of thousands of events, each of which becomes a Manim self.play() call
# and a partial-movie file on disk.  On my machine each event takes an average
# of 4.6 seconds. A 580-event run takes roughly 45+ minutes; beyond that the
# render time becomes impractical.
#
# Pass --force on the command line to override this gate.
# ============================================================================

MAX_ANIMATION_EVENTS = 580


# ============================================================================
# DUALITY PROLOGUE PARAMETERS
# ============================================================================
# These constants control the timing and appearance of the Voronoi-to-graph
# transition animation that precedes the coloring algorithm visualization.
# ============================================================================

VORONOI_STROKE_WIDTH  = 2.0    # Border thickness for Voronoi cell polygons.
VORONOI_STROKE_COLOR  = BLACK  # Border color for Voronoi cell polygons.
VORONOI_FILL_OPACITY  = 1   # Fill opacity for the colored Voronoi cells.

# Phase durations (in seconds, before SPEED_FACTOR is applied).
PROLOGUE_MAP_FADE_IN   = 0.1   # Time to fade in the Voronoi map.
PROLOGUE_MAP_HOLD      = 1.0   # Pause to let the audience see the map.
PROLOGUE_TRANSITION    = 3.0   # Duration of the "melting" transition.
PROLOGUE_PERSIST_HOLD  = 0.2   # Pause showing colored vertices (persistence).
PROLOGUE_WIPE_TO_WHITE = .2   # Time to fade all vertices back to white.
PROLOGUE_PRE_ALGO_PAUSE = 0.2  # Brief pause before the algorithm begins.


# ============================================================================
# GRAPH LOADING
# ============================================================================

def load_graphs(path: str) -> dict:
    """Deserialize the planar graph library from a pickle file.

    Returns a dict[str, nx.Graph] keyed by graph short_name (e.g.
    'RSST_001', 'kempe_fritsch_1').  The pickle is produced by
    generate_planar_pkls.py in the graph_library package.
    """
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data


def resolve_graph_key(graphs: dict, user_input: str) -> str:
    """Resolve user input to an exact graph key.

    Accepts:
      - An exact key:        'RSST_001', 'kempe_fritsch_1'
      - A case-insensitive partial match (must be unique)

    Returns the resolved key, or raises SystemExit with a helpful message.
    """
    # Exact match
    if user_input in graphs:
        return user_input

    # Case-insensitive partial match
    lower = user_input.lower()
    matches = [k for k in graphs if lower in k.lower()]
    if len(matches) == 1:
        print(f"  (Matched '{user_input}' → {matches[0]})")
        return matches[0]
    elif len(matches) > 1:
        print(f"Error: '{user_input}' is ambiguous. Matches:")
        for m in matches[:15]:
            name = graphs[m].graph.get('name', m)
            print(f"  {m:35s}  {name}")
        if len(matches) > 15:
            print(f"  ... and {len(matches) - 15} more")
        sys.exit(2)
    else:
        print(f"Error: '{user_input}' not found in library.")
        print(f"  Use --list to see available graphs.")
        sys.exit(2)


def list_graphs(graphs: dict, filter_text: str = None):
    """Print a formatted listing of available graphs to the console."""
    filtered = graphs
    if filter_text:
        lower = filter_text.lower()
        filtered = {k: v for k, v in graphs.items()
                    if lower in k.lower()
                    or lower in v.graph.get('name', '').lower()
                    or lower in v.graph.get('module', '').lower()}

    if not filtered:
        print(f"No graphs matching '{filter_text}'.")
        return

    print(f"\n{'Key':<35s} {'Name':<35s} {'V':>3s} {'E':>3s}  "
          f"{'Module':<25s}")
    print("-" * 105)

    for key in sorted(filtered.keys()):
        g = filtered[key]
        m = g.graph
        print(f"{key:<35s} {m.get('name', '?'):<35s} "
              f"{m.get('vertices', g.number_of_nodes()):>3d} "
              f"{m.get('edges', g.number_of_edges()):>3d}  "
              f"{m.get('module', '?'):<25s}")

    print(f"\nTotal: {len(filtered)} graphs", end="")
    if filter_text and len(filtered) != len(graphs):
        print(f"  (filtered from {len(graphs)} total)")
    else:
        print()


# ============================================================================
# PLANAR GRAPH STATISTICS
# ============================================================================

def compute_stats(G: nx.Graph) -> dict:
    """Compute structural statistics for a planar graph.

    For a connected planar graph, Euler's formula states V - E + F = 2.
    This function verifies the identity using the combinatorial embedding.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()
    degs = [d for _, d in G.degree()]
    max_deg = max(degs) if degs else 0
    avg_deg = round(2 * m / n, 2) if n > 0 else 0
    comps = nx.number_connected_components(G)

    is_planar, emb = nx.check_planarity(G, counterexample=False)
    faces = None
    euler_ok = False

    if is_planar and n > 0:
        visited_half_edges = set()
        face_count = 0
        for v in emb:
            for w in emb.neighbors_cw_order(v):
                if (v, w) not in visited_half_edges:
                    face_nodes = emb.traverse_face(v, w)
                    face_count += 1
                    for i in range(len(face_nodes)):
                        u = face_nodes[i]
                        nxt = face_nodes[(i + 1) % len(face_nodes)]
                        visited_half_edges.add((u, nxt))
        faces = face_count
        euler_ok = (n - m + faces == 2 * comps)

    return {
        "n": n, "m": m, "maxdeg": max_deg, "avgdeg": avg_deg,
        "comps": comps, "faces": faces, "euler_ok": euler_ok,
    }


# ============================================================================
# COLORING HEURISTICS
# ============================================================================

def _backtrack_coloring(G, order, max_colors):
    """Color the graph using depth-first search with backtracking."""
    events = []
    color = {}

    def dfs(i):
        if i >= len(order):
            return True
        v = order[i]
        used = {color[u] for u in G[v] if u in color}
        for c in range(max_colors):
            if c not in used:
                color[v] = c
                events.append(("color", v, c))
                if dfs(i + 1):
                    return True
                events.append(("uncolor", v))
                color.pop(v, None)
        events.append(("conflict", v))
        return False

    dfs(0)
    return color, events


def greedy_largest_first(G, max_colors=4):
    """Largest-first greedy coloring with backtracking."""
    order = sorted(G.nodes(), key=lambda v: G.degree(v), reverse=True)
    return _backtrack_coloring(G, order, max_colors)


def dsatur_coloring(G, max_colors=4, tiebreak="degree"):
    """DSATUR (Degree of Saturation) coloring heuristic (Brelaz, 1979)."""
    color = {}
    events = []

    def sat_degree(v):
        return len({color[u] for u in G[v] if u in color})

    if tiebreak == "degree":
        key_fn = lambda u: (sat_degree(u), G.degree(u), -u)
    else:
        key_fn = lambda u: (sat_degree(u), u)

    uncolored = set(G.nodes())
    needs_fallback = False

    while uncolored:
        v = max(uncolored, key=key_fn)
        used = {color[u] for u in G[v] if u in color}
        assigned = False
        for c in range(max_colors):
            if c not in used:
                color[v] = c
                events.append(("color", v, c))
                uncolored.remove(v)
                assigned = True
                break
        if not assigned:
            events.append(("conflict", v))
            events.append(("alert", v,
                           "DSATUR needs >4 colors - switching to backtracking"))
            needs_fallback = True
            break

    if needs_fallback:
        for u in list(reversed(list(color.keys()))):
            events.append(("uncolor", u))
        color.clear()
        order = sorted(G.nodes(), key=lambda v: G.degree(v), reverse=True)
        bt_color, bt_events = _backtrack_coloring(G, order, max_colors)
        events.extend(bt_events)
        return bt_color, events

    return color, events


def smallest_last_greedy(G, max_colors=4):
    """Smallest-last ordering with backtracking."""
    Gcopy = G.copy()
    order = []
    while Gcopy:
        v = min(Gcopy, key=lambda x: Gcopy.degree(x))
        order.append(v)
        Gcopy.remove_node(v)
    order.reverse()
    return _backtrack_coloring(G, order, max_colors)


def random_greedy(G, seed=None):
    """Random-order greedy coloring (no backtracking, no color limit)."""
    import random as _random
    nodes = list(G.nodes())
    rng = _random.Random(seed)
    rng.shuffle(nodes)

    color = {}
    events = []
    for v in nodes:
        used = {color[u] for u in G[v] if u in color}
        c = 0
        while c in used:
            c += 1
        color[v] = c
        events.append(("color", v, c))
    return color, events


ALGO_DISPATCH = {
    "Greedy":  greedy_largest_first,
    "DSATUR":  dsatur_coloring,
    "SmlLst":  smallest_last_greedy,
    "Random":  random_greedy,
}


# ============================================================================
# GRAPH LAYOUT
# ============================================================================

def compute_layout(G):
    """Compute 2-D vertex positions for Manim rendering.

    Prefers pre-computed positions stored in G.graph['pos'] by the graph
    library (these were optimized for visual clarity when the graph was
    generated).  Falls back to a planar-seeded spring layout if no
    stored positions exist.

    Returns a dict of {node: np.array([x, y, 0.0])}.
    """
    # Use stored library positions if available
    stored_pos = G.graph.get('pos')
    if stored_pos:
        return {
            v: np.array([float(xy[0]), float(xy[1]), 0.0])
            for v, xy in stored_pos.items()
            if v in G.nodes()
        }

    # Fallback: compute fresh layout
    n = max(1, G.number_of_nodes())

    try:
        pos2d_seed = nx.planar_layout(G)
    except Exception:
        pos2d_seed = None

    pos2d = nx.spring_layout(
        G, seed=1, pos=pos2d_seed,
        k=SPRING_K_MULT / np.sqrt(n),
        iterations=SPRING_ITERS,
    )

    return {
        v: np.array([3.0 * float(xy[0]), 3.0 * float(xy[1]), 0.0])
        for v, xy in pos2d.items()
    }


# ============================================================================
# AUTO-SIZING: compute node radius, edge width, label size per graph
# ============================================================================

def compute_visual_params(n, m, max_degree, scaled_layout, edges):
    """Compute node_radius, edge_stroke_width, and label_font_size for a graph.

    The sizing adapts to **the actual rendered geometry** so that nodes never
    overlap their neighbors and labels remain legible.  This replaces the old
    fixed constants and means new daughter modules (even with 50+ vertices)
    work out-of-the-box without manual tuning.

    Algorithm
    ---------
    1.  **Minimum neighbor distance** — iterate over every edge and find the
        shortest distance between connected vertices in the *scaled* layout.
        The node radius must be < half that distance (with clearance).

    2.  **Vertex-count cap** — even if the layout is spacious, very large
        graphs look cleaner with modestly sized nodes.

    3.  **Edge-density adjustment** — dense graphs (high avg degree) benefit
        from slightly thinner edges so the drawing isn't overwhelmed by ink.

    The edge stroke width and label font size are derived proportionally
    from the chosen radius so everything scales together.

    Parameters
    ----------
    n : int
        Number of vertices.
    m : int
        Number of edges.
    max_degree : int
        Maximum vertex degree (used for density feel).
    scaled_layout : dict
        {vertex: np.array([x, y, 0])} — final positions in Manim coords.
    edges : list[tuple]
        Edge list of the graph.

    Returns
    -------
    node_radius : float
    edge_stroke_width : float
    label_font_size : int
    """
    import math

    # ------------------------------------------------------------------
    # 1.  Minimum edge length in the rendered layout
    # ------------------------------------------------------------------
    min_edge_len = float('inf')
    for u, v in edges:
        pu, pv = scaled_layout.get(u), scaled_layout.get(v)
        if pu is not None and pv is not None:
            dist = float(np.linalg.norm(pu - pv))
            if dist > 1e-9:
                min_edge_len = min(min_edge_len, dist)

    if min_edge_len == float('inf'):
        # No edges or degenerate layout — use defaults
        return (DEFAULT_NODE_RADIUS, DEFAULT_EDGE_STROKE_WIDTH,
                DEFAULT_LABEL_FONT_SIZE)

    # ------------------------------------------------------------------
    # 2.  Radius from geometry: two nodes must not touch along any edge.
    #     Allow ~35 % of the shortest edge for each node's radius, leaving
    #     30 % of that edge as visible "gap" between circles.
    # ------------------------------------------------------------------
    radius_from_geom = min_edge_len * 0.35

    # ------------------------------------------------------------------
    # 3.  Radius cap from vertex count: gently shrink for larger graphs.
    #     Anchored so n≈12 → ~0.30, n≈25 → ~0.22, n≈50 → ~0.16.
    # ------------------------------------------------------------------
    radius_from_n = 0.50 / (1.0 + 0.04 * n)

    # ------------------------------------------------------------------
    # 4.  Pick the tighter constraint, then clamp.
    # ------------------------------------------------------------------
    node_radius = min(radius_from_geom, radius_from_n)
    node_radius = max(0.10, min(0.35, node_radius))       # hard clamp

    # ------------------------------------------------------------------
    # 5.  Edge stroke width — linear in radius, tuned to match:
    #       radius 0.30 → stroke ≈ 5,  radius 0.16 → stroke ≈ 3
    #     Thin out slightly for high-density graphs.
    # ------------------------------------------------------------------
    avg_deg = (2.0 * m / n) if n > 0 else 0
    base_stroke = 14.3 * node_radius + 0.71
    # Reduce slightly for high average degree (more ink on screen)
    density_factor = max(0.65, 1.0 - (avg_deg - 4.5) * 0.05)
    edge_stroke_width = base_stroke * density_factor
    edge_stroke_width = max(1.5, min(6.0, edge_stroke_width))

    # ------------------------------------------------------------------
    # 6.  Label font size — linear in radius, tuned to match:
    #       radius 0.30 → font 22,  radius 0.16 → font 14
    # ------------------------------------------------------------------
    label_font_size = int(round(57.0 * node_radius + 5.0))
    label_font_size = max(10, min(26, label_font_size))

    return node_radius, edge_stroke_width, label_font_size


# ============================================================================
# VORONOI TESSELLATION  (for the duality prologue)
# ============================================================================

def _clip_polygon_rect(poly_pts, x_min, y_min, x_max, y_max):
    """Clip a convex polygon to an axis-aligned rectangle.

    Uses the Sutherland-Hodgman algorithm.  The input ``poly_pts`` is a
    list of ``(x, y)`` tuples defining the polygon vertices in order.
    Returns a (possibly empty) list of ``(x, y)`` tuples for the clipped
    polygon.

    Parameters
    ----------
    poly_pts : list[tuple[float, float]]
        Vertices of the polygon to clip.
    x_min, y_min, x_max, y_max : float
        Bounds of the clipping rectangle.

    Returns
    -------
    list[tuple[float, float]]
        Vertices of the clipped polygon, or [] if entirely outside.
    """
    def _clip_edge(pts, inside_fn, intersect_fn):
        """Clip a polygon against one infinite half-plane."""
        if not pts:
            return []
        out = []
        for i in range(len(pts)):
            curr = pts[i]
            prev = pts[i - 1]
            c_in = inside_fn(curr)
            p_in = inside_fn(prev)
            if p_in and c_in:
                out.append(curr)
            elif p_in and not c_in:
                out.append(intersect_fn(prev, curr))
            elif not p_in and c_in:
                out.append(intersect_fn(prev, curr))
                out.append(curr)
            # else: both outside → skip
        return out

    pts = list(poly_pts)

    # Clip against each of the four rectangle edges.
    # Left edge (x >= x_min)
    pts = _clip_edge(
        pts,
        lambda p: p[0] >= x_min,
        lambda a, b: (
            x_min,
            a[1] + (b[1] - a[1]) * (x_min - a[0]) / (b[0] - a[0])
        ) if abs(b[0] - a[0]) > 1e-12 else a,
    )
    # Right edge (x <= x_max)
    pts = _clip_edge(
        pts,
        lambda p: p[0] <= x_max,
        lambda a, b: (
            x_max,
            a[1] + (b[1] - a[1]) * (x_max - a[0]) / (b[0] - a[0])
        ) if abs(b[0] - a[0]) > 1e-12 else a,
    )
    # Bottom edge (y >= y_min)
    pts = _clip_edge(
        pts,
        lambda p: p[1] >= y_min,
        lambda a, b: (
            a[0] + (b[0] - a[0]) * (y_min - a[1]) / (b[1] - a[1]),
            y_min,
        ) if abs(b[1] - a[1]) > 1e-12 else a,
    )
    # Top edge (y <= y_max)
    pts = _clip_edge(
        pts,
        lambda p: p[1] <= y_max,
        lambda a, b: (
            a[0] + (b[0] - a[0]) * (y_max - a[1]) / (b[1] - a[1]),
            y_max,
        ) if abs(b[1] - a[1]) > 1e-12 else a,
    )

    return pts


def compute_voronoi_cells(vertex_positions_2d, clip_bounds):
    """Compute clipped Voronoi cells for a set of 2-D points.

    Mirror points are added far outside the clipping rectangle to guarantee
    that every real vertex's Voronoi cell is finite before clipping.

    Parameters
    ----------
    vertex_positions_2d : dict[int, tuple[float, float]]
        Mapping from vertex ID to ``(x, y)`` coordinates.
    clip_bounds : tuple[float, float, float, float]
        ``(x_min, y_min, x_max, y_max)`` defining the clipping rectangle.

    Returns
    -------
    dict[int, list[tuple[float, float]]]
        Mapping from vertex ID to a list of ``(x, y)`` polygon corners
        for the clipped Voronoi cell.  Vertices whose cells vanish after
        clipping are omitted.
    """
    if not HAS_SCIPY:
        return {}

    ids = sorted(vertex_positions_2d.keys())
    if len(ids) < 2:
        return {}

    points = np.array([vertex_positions_2d[v] for v in ids])

    x_min, y_min, x_max, y_max = clip_bounds
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    span = max(x_max - x_min, y_max - y_min) * 5.0

    # Eight mirror points guarantee all real cells are finite.
    mirror = np.array([
        [cx - span, cy - span],
        [cx + span, cy - span],
        [cx - span, cy + span],
        [cx + span, cy + span],
        [cx - span, cy],
        [cx + span, cy],
        [cx,        cy - span],
        [cx,        cy + span],
    ])

    all_pts = np.vstack([points, mirror])

    try:
        vor = ScipyVoronoi(all_pts)
    except Exception:
        return {}

    cells = {}
    for i, vid in enumerate(ids):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        if -1 in region or len(region) == 0:
            continue
        poly = [(vor.vertices[j][0], vor.vertices[j][1]) for j in region]
        clipped = _clip_polygon_rect(poly, x_min, y_min, x_max, y_max)
        if len(clipped) >= 3:
            cells[vid] = clipped

    return cells


# ============================================================================
# MANIM SCENE  --  FourColorScene
# ============================================================================

class FourColorScene(Scene):
    """Manim scene: duality prologue + coloring heuristic animation.

    The scene is composed of four visual layers:

    1.  **Prologue** -- Voronoi map → graph transition (Face-to-Vertex
        duality).  Demonstrates that coloring the map's regions is
        equivalent to coloring the dual graph's vertices.

    2.  **Header** -- Scene Card bar: dark badge (graph name + module)
        followed by Euler equation cells (V − E + F = 2).

    3.  **Graph** -- Labeled vertices and edges, animated by the heuristic.

    4.  **Footer/HUD** -- Algorithm badge + degree stats on the left;
        live running counters (Colors, Assign, Back) on the right.

    Parameters
    ----------
    G : nx.Graph
        The planar graph to animate.
    stats : dict
        Output of ``compute_stats(G)``.
    events : list[tuple]
        Coloring event sequence from a heuristic.
    coloring : dict[int, int]
        Pre-computed final coloring (vertex → color index).
    graph_title : str
        Display title (e.g., ``"Fritsch Graph"`` or ``"RSST Configuration 42"``).
    algo_name : str
        Algorithm name shown in the header.
    """

    def __init__(self, G, stats, events, coloring,
                 graph_title, algo_name, graph_module="unknown", **kwargs):
        self.G = G
        self.stats = stats
        self.events_list = events
        self.coloring = coloring
        self.graph_title = graph_title
        self.algo_name = algo_name
        self.graph_module = graph_module
        super().__init__(**kwargs)

    # ------------------------------------------------------------------ #
    #  construct()                                                       #
    # ------------------------------------------------------------------ #
    def construct(self):
        self.camera.background_color = WHITE

        G = self.G
        vertices = list(G.nodes())
        edges = list(G.edges())
        s = self.stats

        # ================================================================ #
        #  HEADER  —  Scene Card design                                    #
        # ================================================================ #
        # Layout:                                                          #
        #   [DARK BADGE] | V − E + F = 2  (Euler equation as stat cells)   #
        #                                                                  #
        # The dark badge holds the graph name and module tag.              #
        # The remaining width is divided into 4 equal cells whose large    #
        # numbers and small labels spell out the Euler formula.            #
        # Operators (−, +, =) are placed on the cell separator lines.      #
        # ================================================================ #

        n, m = s["n"], s["m"]
        f_val = s["faces"] if s["faces"] is not None else "?"
        euler_result = n - m + (s["faces"] or 0)
        euler_ok = s["euler_ok"]

        # --- Coordinates --------------------------------------------------
        h_left  = GRAPH_X_MIN           # −3.85
        h_right = GRAPH_X_MAX           # +3.85
        h_top   = HEADER_TOP            # +3.85
        h_bot   = HEADER_BOT            # +2.80
        h_w     = h_right - h_left      #  7.70
        h_h     = HEADER_HEIGHT         #  1.05
        h_mid_y = (h_top + h_bot) / 2   # vertical midpoint of header

        badge_w = h_w * BADGE_WIDTH_FRAC  # ~1.54

        # Y positions for numbers and labels inside header cells.
        # Defined here (before badge) because the module tag also uses label_y.
        num_y   = h_mid_y + 0.12            # numbers sit above center
        label_y = h_bot + 0.18              # labels sit near bottom

        # --- 1. Dark badge (black rectangle with white text) --------------
        badge_bg = Rectangle(
            width=badge_w, height=h_h,
            fill_color="#1a1a1a", fill_opacity=1.0,
            stroke_color=BLACK, stroke_width=2,
        )
        badge_bg.move_to(np.array([h_left + badge_w / 2, h_mid_y, 0]))

        # Split the graph title into two lines for the badge.
        title_words = self.graph_title.split()
        if len(title_words) >= 2:
            badge_line1 = title_words[0]
            badge_line2 = " ".join(title_words[1:])
        else:
            badge_line1 = self.graph_title
            badge_line2 = ""

        badge_name_1 = Text(
            badge_line1, font_size=BADGE_NAME_FONT_SIZE,
            color=WHITE, weight=BOLD,
        )
        if badge_line2:
            badge_name_2 = Text(
                badge_line2, font_size=BADGE_NAME_FONT_SIZE,
                color=WHITE, weight=BOLD,
            )
            badge_name = VGroup(badge_name_1, badge_name_2).arrange(
                DOWN, aligned_edge=LEFT, buff=0.04,
            )
        else:
            badge_name = badge_name_1

        # Module tag — uses the SAME font as equation cell labels so it
        # aligns visually.  Positioned at label_y to sit on the same
        # baseline as VERTICES, EDGES, FACES, EULER.
        module_display = MODULE_DISPLAY_NAMES.get(
            self.graph_module,
            self.graph_module.upper().replace("_", " ")[:18],
        )
        badge_module = Text(
            module_display, font_size=HEADER_LABEL_FONT_SIZE,
            font=HEADER_FONT, color=WHITE,
        )

        # Fit badge_name inside the badge width, with padding
        max_text_w = badge_w - 0.25
        if badge_name.width > max_text_w:
            badge_name.scale(max_text_w / badge_name.width)
        if badge_module.width > max_text_w:
            badge_module.scale(max_text_w / badge_module.width)

        # Position graph name: vertically centered between header top
        # and where the module label will sit, horizontally left-padded
        badge_pad_x = h_left + 0.15 + badge_name.width / 2
        name_center_y = (h_top + label_y) / 2
        badge_name.move_to(np.array([badge_pad_x, name_center_y, 0]))

        # Position module tag at label_y (aligned with VERTICES etc.)
        badge_module.move_to(np.array([
            h_left + 0.15 + badge_module.width / 2,
            label_y, 0
        ]))

        badge_group = VGroup(badge_bg, badge_name, badge_module)

        # --- 2. Equation cells  (V − E + F = 2) --------------------------
        eq_left  = h_left + badge_w
        eq_right = h_right
        eq_w     = eq_right - eq_left       # width available for 4 cells
        cell_w   = eq_w / 4                 # each cell's width

        # Padding from the left edge of each cell for left-aligned content
        CELL_LEFT_PAD = 0.18

        def _make_cell(num_str, label_str, cell_left_x):
            """Build one equation cell: big number + small label, LEFT-justified."""
            num = Text(
                str(num_str), font_size=HEADER_NUM_FONT_SIZE,
                font=HEADER_FONT, color=BLACK, weight=BOLD,
            )
            # Left-align: position so left edge is at cell_left_x + padding
            num.move_to(np.array([
                cell_left_x + CELL_LEFT_PAD + num.width / 2,
                num_y, 0
            ]))
            lbl = Text(
                label_str, font_size=HEADER_LABEL_FONT_SIZE,
                font=HEADER_FONT, color="#364153",
            )
            lbl.move_to(np.array([
                cell_left_x + CELL_LEFT_PAD + lbl.width / 2,
                label_y, 0
            ]))
            return VGroup(num, lbl)

        # Cell LEFT-edge x-coordinates (not centers)
        cl = [eq_left + cell_w * i for i in range(4)]

        cell_v = _make_cell(n,            "VERTICES", cl[0])
        cell_e = _make_cell(m,            "EDGES",    cl[1])
        cell_f = _make_cell(f_val,        "FACES",    cl[2])

        # Result cell: number + check mark + "EULER" label, left-justified
        result_num = Text(
            str(euler_result), font_size=HEADER_NUM_FONT_SIZE,
            font=HEADER_FONT, color=BLACK, weight=BOLD,
        )
        result_num.move_to(np.array([
            cl[3] + CELL_LEFT_PAD + result_num.width / 2,
            num_y, 0
        ]))

        euler_mark = "\u2713" if euler_ok else "\u2717"
        euler_color = "#2a9d2a" if euler_ok else "#cc2222"
        result_check = Text(
            euler_mark, font_size=EULER_CHECK_FONT_SIZE,
            color=euler_color, weight=BOLD,
        )
        result_check.next_to(result_num, RIGHT, buff=0.10)

        result_label = Text(
            "EULER", font_size=HEADER_LABEL_FONT_SIZE,
            font=HEADER_FONT, color="#364153",
        )
        result_label.move_to(np.array([
            cl[3] + CELL_LEFT_PAD + result_label.width / 2,
            label_y, 0
        ]))

        cell_result = VGroup(result_num, result_check, result_label)

        # --- 3. Operators on separator lines (−, +, =) --------------------
        # Operators are RIGHT-justified: their right edge sits just left of
        # the separator line, with a small gap.
        OP_RIGHT_PAD = 0.08   # gap between operator right edge and sep line

        def _make_op(symbol, sep_line_x):
            """Place an operator right-justified against a separator line."""
            op = Text(
                symbol, font_size=HEADER_OP_FONT_SIZE,
                font=HEADER_FONT, color="#999999",
            )
            # Position so right edge is at sep_line_x - OP_RIGHT_PAD
            op.move_to(np.array([
                sep_line_x - OP_RIGHT_PAD - op.width / 2,
                num_y, 0
            ]))
            # Small white rectangle behind the operator to break the
            # separator line visually.
            bg = Rectangle(
                width=op.width + 0.08, height=op.height + 0.04,
                fill_color=WHITE, fill_opacity=1.0, stroke_width=0,
            )
            bg.move_to(op)
            return VGroup(bg, op)

        sep_x = [eq_left + cell_w * i for i in range(1, 4)]  # 3 separators
        op_minus  = _make_op("\u2212", sep_x[0])   # − (minus sign)
        op_plus   = _make_op("+",      sep_x[1])
        op_equals = _make_op("=",      sep_x[2])

        # --- 4. Border lines and separators -------------------------------
        # Outer header border
        header_border = Rectangle(
            width=h_w, height=h_h,
            stroke_color=BLACK, stroke_width=2.5,
            fill_opacity=0,
        )
        header_border.move_to(np.array([(h_left + h_right) / 2, h_mid_y, 0]))

        # Vertical separator lines between cells
        sep_lines = VGroup()
        # Badge right edge (already has contrast from black bg)
        for sx in sep_x:
            line = Line(
                start=np.array([sx, h_top, 0]),
                end=np.array([sx, h_bot, 0]),
                stroke_width=1.5, color=GRAY_B,
            )
            sep_lines.add(line)

        # Badge-to-cells separator (slightly heavier)
        badge_sep = Line(
            start=np.array([eq_left, h_top, 0]),
            end=np.array([eq_left, h_bot, 0]),
            stroke_width=2, color=BLACK,
        )

        # Bottom rule spanning full width
        header_rule = Line(
            start=np.array([h_left, h_bot, 0]),
            end=np.array([h_right, h_bot, 0]),
            stroke_width=3, color=BLACK,
        )

        # --- 5. Assemble the header group ---------------------------------
        header_group = VGroup(
            header_border,
            badge_group,
            badge_sep,
            sep_lines,
            cell_v, cell_e, cell_f, cell_result,
            op_minus, op_plus, op_equals,
            header_rule,
        )

        # ============================================================== #
        #  GRAPH  --  vertices, edges, and labels                        #
        # ============================================================== #

        layout = compute_layout(G)

        # --- Pre-scale layout positions to fit usable area ----------------
        # This avoids scaling the VGroup (which distorts node radii and
        # stroke widths).  Instead, we map the raw layout coordinates into
        # the FIXED content area and then compute ideal visual parameters.

        x_min = CONTENT_X_MIN
        x_max = CONTENT_X_MAX
        y_min = CONTENT_Y_MIN
        y_max = CONTENT_Y_MAX
        usable_w = USABLE_W
        usable_h = USABLE_H

        # Compute bounding box of raw layout
        all_x = [p[0] for p in layout.values()]
        all_y = [p[1] for p in layout.values()]
        raw_x_range = (max(all_x) - min(all_x)) if all_x else 1.0
        raw_y_range = (max(all_y) - min(all_y)) if all_y else 1.0
        raw_x_range = max(raw_x_range, 0.001)
        raw_y_range = max(raw_y_range, 0.001)

        cx_layout = (max(all_x) + min(all_x)) / 2
        cy_layout = (max(all_y) + min(all_y)) / 2
        x_center = (x_min + x_max) / 2
        y_center = (y_max + y_min) / 2

        # --- Two-pass sizing: estimate layout, compute ideal params, -----
        #     then re-scale with the correct padding.                     --
        # Pass 1: scale with default radius to get initial positions
        est_padding = DEFAULT_NODE_RADIUS + 0.15
        est_eff_w = usable_w - est_padding * 2
        est_eff_h = usable_h - est_padding * 2
        est_scale = min(est_eff_w / raw_x_range, est_eff_h / raw_y_range)

        est_layout = {}
        for v, pos in layout.items():
            est_layout[v] = np.array([
                (pos[0] - cx_layout) * est_scale + x_center,
                (pos[1] - cy_layout) * est_scale + y_center,
                0.0,
            ])

        # Compute auto-sized visual parameters from the estimated layout
        NODE_RADIUS, EDGE_STROKE_WIDTH, LABEL_FONT_SIZE = (
            compute_visual_params(
                n=s["n"], m=s["m"], max_degree=s["maxdeg"],
                scaled_layout=est_layout, edges=edges,
            )
        )

        # Pass 2: re-scale with the actual computed radius for padding
        padding = NODE_RADIUS + 0.15
        effective_w = usable_w - padding * 2
        effective_h = usable_h - padding * 2

        scale_factor = min(
            effective_w / raw_x_range,
            effective_h / raw_y_range,
        )

        scaled_layout = {}
        for v, pos in layout.items():
            scaled_layout[v] = np.array([
                (pos[0] - cx_layout) * scale_factor + x_center,
                (pos[1] - cy_layout) * scale_factor + y_center,
                0.0,
            ])

        g = Graph(
            vertices, edges,
            layout=scaled_layout,
            edge_config={
                "stroke_width": EDGE_STROKE_WIDTH,
                "color": EDGE_COLOR,
            },
            vertex_config={
                "radius": NODE_RADIUS,
                "stroke_width": NODE_STROKE_WIDTH,
                "stroke_color": BLACK,
                "fill_color": WHITE,
                "fill_opacity": 1.0,
            },
        )

        label_group = VGroup(*[
            Text(str(v), color=BLACK, font_size=LABEL_FONT_SIZE)
            .move_to(g.vertices[v].get_center())
            .set_z_index(10)
            for v in vertices
        ])

        # ================================================================ #
        #  VORONOI DUALITY PROLOGUE                                        #
        # ================================================================ #
        #                                                                  #
        #  This section computes the Voronoi tessellation from the FINAL   #
        #  positioned vertex coordinates, builds colored polygon mobjects, #
        #  and animates the "primal map → dual graph" transition.          #
        #                                                                  #
        # ================================================================ #

        # Extract the final on-screen 2-D positions from the Manim Graph
        # object (after scaling and centering).
        final_pos_2d = {}
        for v in vertices:
            center = g.vertices[v].get_center()
            final_pos_2d[v] = (float(center[0]), float(center[1]))

        # The clipping rectangle fills to the graph border (not the inset
        # content area), so Voronoi cells tile the entire visible middle.
        clip_bounds = (GRAPH_X_MIN, GRAPH_Y_MIN, GRAPH_X_MAX, GRAPH_Y_MAX)

        voronoi_cells = compute_voronoi_cells(final_pos_2d, clip_bounds)
        do_prologue = len(voronoi_cells) >= 2

        voronoi_mobjects = {}   # vertex_id → Manim Polygon
        if do_prologue:
            for v, cell_pts in voronoi_cells.items():
                # Convert 2-D cell points to Manim 3-D coordinates.
                corners = [np.array([p[0], p[1], 0.0]) for p in cell_pts]

                # Look up the color from the pre-computed coloring.
                c_idx = self.coloring.get(v, 0)
                hex_c = PASTEL_HEX_COLORS[c_idx % len(PASTEL_HEX_COLORS)]

                poly = Polygon(
                    *corners,
                    fill_color=hex_c,
                    fill_opacity=VORONOI_FILL_OPACITY,
                    stroke_color=VORONOI_STROKE_COLOR,
                    stroke_width=VORONOI_STROKE_WIDTH,
                )
                voronoi_mobjects[v] = poly

        # ====================================================================== #
        #  HUD / FOOTER  —  Scene Card design                                    #
        # ====================================================================== #
        # Layout:                                                                #
        #   [ALGO_BADGE] Δ=maxdeg avg=avgdeg  ·····  Colors N  Assign N  Back N  #
        # ====================================================================== #

        # Footer rule line (drawn once, stays for the whole scene)
        footer_rule = Line(
            start=np.array([GRAPH_X_MIN, FOOTER_TOP, 0]),
            end=np.array([GRAPH_X_MAX, FOOTER_TOP, 0]),
            stroke_width=3, color=BLACK,
        )

        # Map algorithm names to pastel badge colors
        ALGO_BADGE_COLORS = {
            "Greedy": "#D5B1FF",   # purple
            "DSATUR": "#8AAFFF",   # blue
            "SmlLst": "#FF8AAF",   # pink
            "Random": "#FFDA8A",   # yellow
        }
        algo_badge_hex = ALGO_BADGE_COLORS.get(self.algo_name, "#D5B1FF")

        hud_mob = None
        footer_static = None    # the algo badge + degree stats (don't change)

        def build_footer_static():
            """Build the left side of the footer (algo badge + degree stats).
            Called once; these elements don't change during the animation."""
            nonlocal footer_static
            # Algo badge: colored rounded rectangle with algo name
            badge_text = Text(
                self.algo_name.upper(),
                font_size=HUD_ALGO_FONT_SIZE,
                font=HEADER_FONT, color=BLACK, weight=BOLD,
            )
            badge_bg = RoundedRectangle(
                width=badge_text.width + 0.22,
                height=badge_text.height + 0.12,
                corner_radius=0.06,
                fill_color=algo_badge_hex, fill_opacity=1.0,
                stroke_color="#00000022", stroke_width=1,
            )
            badge_bg.move_to(badge_text)
            algo_badge = VGroup(badge_bg, badge_text)

            # Degree stats
            deg_stats = Text(
                f"\u0394={s['maxdeg']}  avg={s['avgdeg']:.1f}",
                font_size=HUD_FONT_SIZE,
                font=HEADER_FONT, color="#666666",
            )

            left_group = VGroup(algo_badge, deg_stats).arrange(RIGHT, buff=0.20)

            # Position in the footer
            footer_mid_y = (FOOTER_TOP + FOOTER_BOT) / 2
            left_group.move_to(np.array([GRAPH_X_MIN + left_group.width / 2 + 0.15,
                                         footer_mid_y, 0]))
            footer_static = left_group
            return footer_static

        def update_hud(assignments, backtracks, conflicts, colors_used_count):
            """Update the right-side counters in the footer."""
            nonlocal hud_mob
            if hud_mob is not None:
                self.remove(hud_mob)
            # Tight spacing: minimal gap after numbers, readable labels
            hud_str = (
                f"Colors {colors_used_count:>2d} "
                f"Assign {assignments:>3d} "
                f"Back {backtracks:>2d}"
            )
            footer_mid_y = (FOOTER_TOP + FOOTER_BOT) / 2
            hud_mob = Text(
                hud_str,
                font_size=HUD_FONT_SIZE,
                font=HEADER_FONT,
                color=BLACK,
            )
            # Push counters to the right edge
            hud_mob.move_to(np.array([
                GRAPH_X_MAX - hud_mob.width / 2 - 0.12,
                footer_mid_y, 0
            ]))
            self.add(hud_mob)

        alert_mob = None

        def show_alert(msg):
            nonlocal alert_mob
            if alert_mob is not None:
                self.remove(alert_mob)
            alert_mob = Text(
                msg,
                font_size=HUD_FONT_SIZE,
                color=RED,
            )
            # Position alert just above the footer rule
            alert_mob.move_to(np.array([0, FOOTER_TOP + 0.25, 0]))
            self.play(FadeIn(alert_mob), run_time=0.3 * SPEED_FACTOR)
            self.wait(0.8 * SPEED_FACTOR)
            self.play(FadeOut(alert_mob), run_time=0.3 * SPEED_FACTOR)
            alert_mob = None

        # ============================================================== #
        #  ANIMATION  --  PHASE 0: Header + Footer chrome                #
        # ============================================================== #

        # Outer frame border — black border around entire image
        outer_border = Rectangle(
            width=_FW - 0.02, height=_FH - 0.02,
            stroke_color=BLACK, stroke_width=4,
            fill_opacity=0,
        )
        outer_border.move_to(ORIGIN)
        self.add(outer_border)

        # Inner graph area border — thin black rectangle framing the
        # middle section between header rule and footer rule
        graph_border = Rectangle(
            width=BORDER_W,
            height=BORDER_H,
            stroke_color=BLACK, stroke_width=2,
            fill_opacity=0,
        )
        graph_border.move_to(np.array([0, (GRAPH_Y_MAX + GRAPH_Y_MIN) / 2, 0]))
        self.add(graph_border)

        self.add(header_group)
        self.add(footer_rule)
        self.add(build_footer_static())

        # ============================================================== #
        #  ANIMATION  --  PROLOGUE (if Voronoi cells were computed)      #
        # ============================================================== #

        if do_prologue:
            # ----- Phase 1: Fade in the colored Voronoi map -----
            voronoi_group = VGroup(*voronoi_mobjects.values())
            # Place the map behind where the graph will appear.
            voronoi_group.set_z_index(-1)

            self.play(
                FadeIn(voronoi_group),
                run_time=PROLOGUE_MAP_FADE_IN * SPEED_FACTOR,
            )
            self.wait(PROLOGUE_MAP_HOLD * SPEED_FACTOR)

            # ----- Phase 2: "Melting" transition -----
            # Pre-color graph vertices to match their Voronoi cells.
            for v in vertices:
                c_idx = self.coloring.get(v, 0)
                hex_c = PASTEL_HEX_COLORS[c_idx % len(PASTEL_HEX_COLORS)]
                g.vertices[v].set_fill(hex_c, opacity=1.0)

            # Initially hide the graph edges so they can fade in.
            for e_key in g.edges:
                g.edges[e_key].set_stroke(opacity=0.0)

            # Initially scale vertices to near-zero so they grow in.
            for v in vertices:
                g.vertices[v].save_state()
                g.vertices[v].scale(0.01)
                g.vertices[v].set_stroke(opacity=0.0)

            # Add the graph (invisible dots + invisible edges) so
            # we can animate them appearing.
            self.add(g)

            # Build the simultaneous animation lists:
            #   (a) Voronoi cells shrink toward their center and fade out.
            #   (b) Graph vertices grow from zero to full size.
            #   (c) Graph edges fade in.
            shrink_anims = []
            for v, poly in voronoi_mobjects.items():
                target_center = g.vertices[v].get_center()
                shrink_anims.append(
                    poly.animate
                    .scale(0.02, about_point=target_center)
                    .set_fill(opacity=0.0)
                    .set_stroke(opacity=0.0)
                )

            grow_anims = []
            for v in vertices:
                grow_anims.append(g.vertices[v].animate.restore())

            edge_anims = []
            for e_key in g.edges:
                edge_anims.append(
                    g.edges[e_key].animate.set_stroke(opacity=1.0)
                )

            self.play(
                *shrink_anims,
                *grow_anims,
                *edge_anims,
                run_time=PROLOGUE_TRANSITION * SPEED_FACTOR,
            )

            # Clean up: remove the now-invisible Voronoi polygons.
            self.remove(voronoi_group)

            # ----- Phase 3: Color persistence -----
            # The graph is now visible with colored vertices.  Pause
            # so the audience can see vertex ↔ region correspondence.
            self.add(label_group)
            self.bring_to_front(label_group)
            self.wait(PROLOGUE_PERSIST_HOLD * SPEED_FACTOR)

            # ----- Phase 4: Wipe colors to white -----
            wipe_anims = [
                g.vertices[v].animate.set_fill(WHITE, opacity=1.0)
                for v in vertices
            ]
            self.play(
                *wipe_anims,
                run_time=PROLOGUE_WIPE_TO_WHITE * SPEED_FACTOR,
            )
            self.wait(PROLOGUE_PRE_ALGO_PAUSE * SPEED_FACTOR)

        else:
            # ----- Fallback: original graph creation (no prologue) -----
            self.play(Create(g), run_time=1.5)
            self.add(label_group)

        self.bring_to_front(label_group)
        self.wait(0.25)

        # ============================================================== #
        #  ANIMATION  --  COLORING ALGORITHM                             #
        # ============================================================== #

        update_hud(0, 0, 0, 0)

        assignments = 0
        backtracks = 0
        conflicts = 0
        colors_used = set()

        for ev in self.events_list:
            etype = ev[0]

            if etype == "color":
                v, c = ev[1], ev[2]
                colors_used.add(c)
                assignments += 1
                hex_c = PASTEL_HEX_COLORS[c % len(PASTEL_HEX_COLORS)]
                self.play(
                    g.vertices[v].animate.set_fill(hex_c, opacity=1.0),
                    run_time=0.2 * SPEED_FACTOR,
                )

            elif etype == "uncolor":
                v = ev[1]
                backtracks += 1
                self.play(
                    g.vertices[v].animate.set_fill(WHITE, opacity=1.0),
                    run_time=0.1 * SPEED_FACTOR,
                )

            elif etype == "conflict":
                v = ev[1]
                conflicts += 1
                self.play(
                    Flash(g.vertices[v], color=RED, flash_radius=0.4),
                    run_time=0.5 * SPEED_FACTOR,
                )

            elif etype == "alert":
                msg = ev[2]
                show_alert(msg)

            self.bring_to_front(label_group)
            update_hud(assignments, backtracks, conflicts, len(colors_used))

        self.bring_to_front(label_group)
        self.wait(1.0 * SPEED_FACTOR)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Parse arguments, run coloring, render video, write metadata."""

    # --- Handle --list mode -----------------------------------------------
    if len(sys.argv) >= 2 and sys.argv[1] == "--list":
        graphs = load_graphs(GRAPHS_PKL_PATH)
        filter_text = sys.argv[2] if len(sys.argv) > 2 else None
        list_graphs(graphs, filter_text)
        return

    if len(sys.argv) < 3:
        print("Usage: python coloring_animation.py <GRAPH_KEY> <ALGO_NAME> [seed] [--force]")
        print()
        print("  GRAPH_KEY : Graph key string (e.g. RSST_001, kempe_fritsch_1)")
        print("  ALGO_NAME : Greedy | DSATUR | SmlLst | Random")
        print("  seed      : (optional) integer seed for Random algo")
        print("  --force   : override the animation safety gate and render")
        print(f"              even if events exceed {MAX_ANIMATION_EVENTS}")
        print()
        print("  python coloring_animation.py --list          # show all graphs")
        print("  python coloring_animation.py --list kempe    # filter by keyword")
        sys.exit(1)

    # --- Parse positional args and --force flag ---------------------------
    force_render = "--force" in sys.argv
    positional = [a for a in sys.argv[1:] if a != "--force"]

    if len(positional) < 2:
        print("Error: need at least GRAPH_KEY and ALGO_NAME.")
        print("  python coloring_animation.py <GRAPH_KEY> <ALGO_NAME> [seed] [--force]")
        sys.exit(1)

    graph_input = positional[0]
    algo_name = positional[1]
    seed = int(positional[2]) if len(positional) > 2 else None

    if algo_name not in ALGO_DISPATCH:
        print(f"Error: unknown algorithm '{algo_name}'.")
        print(f"  Choose from: {', '.join(ALGO_DISPATCH.keys())}")
        sys.exit(2)

    graphs = load_graphs(GRAPHS_PKL_PATH)
    graph_key = resolve_graph_key(graphs, graph_input)
    G = graphs[graph_key]
    stats = compute_stats(G)

    # --- Build display title from library metadata ------------------------
    meta = G.graph
    graph_name = meta.get('name', graph_key)
    graph_module = meta.get('module', 'unknown')

    # Compact title for the header: name (or key if name is very long)
    if len(graph_name) > 30:
        graph_title = graph_key
    else:
        graph_title = graph_name

    print(f"\n  Graph:     {graph_name}")
    print(f"  Key:       {graph_key}")
    print(f"  Module:    {graph_module}")
    print(f"  V={stats['n']}  E={stats['m']}  "
          f"MaxDeg={stats['maxdeg']}  AvgDeg={stats['avgdeg']}")
    print(f"  Algorithm: {algo_name}")

    # --- Run the selected coloring heuristic ------------------------------
    t_start = time.perf_counter()

    if algo_name == "Random":
        coloring, events = random_greedy(G, seed=seed)
    elif algo_name == "DSATUR":
        coloring, events = dsatur_coloring(G, max_colors=4, tiebreak="degree")
    else:
        coloring, events = ALGO_DISPATCH[algo_name](G)

    t_end = time.perf_counter()
    algo_time_ms = round((t_end - t_start) * 1000, 2)
    print(f"  Time:      {algo_time_ms} ms")

    # --- Event report and render-time estimate ----------------------------
    n_color    = sum(1 for e in events if e[0] == "color")
    n_uncolor  = sum(1 for e in events if e[0] == "uncolor")
    n_conflict = sum(1 for e in events if e[0] == "conflict")
    n_alert    = sum(1 for e in events if e[0] == "alert")
    n_total    = len(events)

    # Estimated Manim render time per event type (seconds of wall-clock
    # per self.play() call).  Calibrated empirically on the author's machine.
    # Adjust these if your hardware is significantly faster or slower.
    EST_SEC_COLOR    = 4.0
    EST_SEC_UNCOLOR  = 4.0
    EST_SEC_CONFLICT = 4.0
    EST_SEC_ALERT    = 4.0

    est_seconds = (
        n_color    * EST_SEC_COLOR
        + n_uncolor  * EST_SEC_UNCOLOR
        + n_conflict * EST_SEC_CONFLICT
        + n_alert    * EST_SEC_ALERT
        + 25 
    )
    est_minutes = est_seconds / 60.0

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │         ALGORITHM  EVENT  REPORT            │")
    print("  ├─────────────────────────────────────────────┤")
    print(f"  │  color   (assignments) : {n_color:>7,d}            │")
    print(f"  │  uncolor (backtracks)  : {n_uncolor:>7,d}            │")
    print(f"  │  alert                 : {n_alert:>7,d}            │")
    print("  ├─────────────────────────────────────────────┤")
    print(f"  │  TOTAL EVENTS          : {n_total:>7,d}            │")
    print(f"  │  TOTAL ANIMATIONS*     : {n_total+3:>7,d}            │")
    print("  ├─────────────────────────────────────────────┤")
    print(f"  │  Est. render time      : {est_minutes:>7.1f} min        │")
    print(f"  │  Safety gate           : {MAX_ANIMATION_EVENTS:>7,d}            │")
    print("  └─────────────────────────────────────────────┘")
    print("  * Each event = 1 Manim self.play() call = 1 partial movie file")
    print("    (+25 for prologue animations)")
    print()

    if n_total > MAX_ANIMATION_EVENTS and not force_render:
        print(f"  ╔═══════════════════════════════════════════════╗")
        print(f"  ║  RENDER REFUSED — {n_total:,d} events exceeds gate   ║")
        print(f"  ║  of {MAX_ANIMATION_EVENTS:,d}.                                      ║")
        print(f"  ║                                               ║")
        print(f"  ║  This would take ~{est_minutes:.0f} min to render.          ║")
        print(f"  ║                                               ║")
        print(f"  ║  Options:                                     ║")
        print(f"  ║    1. Try a smarter algorithm:                ║")
        print(f"  ║         DSATUR or SmlLst often need far       ║")
        print(f"  ║         fewer backtracks than Greedy.         ║")
        print(f"  ║    2. Pass --force to override:               ║")
        print(f"  ║         python coloring_animation.py \\          ║")
        print(f"  ║           {graph_key} {algo_name} --force          ║")
        print(f"  ╚═══════════════════════════════════════════════╝")
        sys.exit(3)

    if n_total > MAX_ANIMATION_EVENTS and force_render:
        print(f"  ⚠  --force active: rendering {n_total:,d} events "
              f"(~{est_minutes:.0f} min).  Godspeed.")
        print()

    # --- Prepare output directories ---------------------------------------
    vid_dir = Path(VIDEO_OUTPUT_DIR)
    vid_dir.mkdir(parents=True, exist_ok=True)
    json_dir = Path(JSON_OUTPUT_DIR)
    json_dir.mkdir(parents=True, exist_ok=True)

    dt_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    # Use graph_key for file names — clean, unique, sortable
    base_name = f"{graph_key}_{algo_name}_{dt_stamp}"

    # --- Render the Manim scene -------------------------------------------
    with tempconfig({
        "pixel_width":  PIXEL_WIDTH,
        "pixel_height": PIXEL_HEIGHT,
        "frame_rate":   FRAME_RATE,
        "frame_width":  FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "preview":      False,
        "media_dir":    MANIM_MEDIA_DIR,
        "output_file":  base_name,
        "background_color": WHITE,
    }):
        scene = FourColorScene(
            G, stats, events,
            coloring=coloring,
            graph_title=graph_title,
            algo_name=algo_name,
            graph_module=graph_module,
        )
        scene.render()

        produced = Path(scene.renderer.file_writer.movie_file_path)
        final_video = vid_dir / f"{base_name}.mp4"
        if produced.exists():
            shutil.copy2(produced, final_video)
            print(f"\n[OK] Video -> {final_video}")
        else:
            print(f"\n[WARN] Render done but file not found: {produced}")

    # --- Write per-run JSON metadata --------------------------------------
    num_colors = (max(coloring.values()) + 1) if coloring else 0
    run_meta = {
        "graph_key":   graph_key,
        "graph_name":  graph_name,
        "module":      graph_module,
        "source":      meta.get('source', ''),
        "algorithm":   algo_name,
        "seed":        seed,
        "datetime":    dt_stamp,
        "n":           stats["n"],
        "m":           stats["m"],
        "maxdeg":      stats["maxdeg"],
        "avgdeg":      stats["avgdeg"],
        "comps":       stats["comps"],
        "faces":       stats["faces"],
        "euler_ok":    stats["euler_ok"],
        "colors_used": num_colors,
        "assignments": sum(1 for e in events if e[0] == "color"),
        "backtracks":  sum(1 for e in events if e[0] == "uncolor"),
        "conflicts":   sum(1 for e in events if e[0] == "conflict"),
    }
    json_path = json_dir / f"{base_name}.json"
    with open(json_path, "w") as f:
        json.dump(run_meta, f, indent=2)
    print(f"[OK] Metadata -> {json_path}")

    # --- Append to leaderboard CSV ----------------------------------------
    lb_dir = Path(LEADERBOARD_DIR)
    lb_dir.mkdir(parents=True, exist_ok=True)
    lb_path = lb_dir / "leaderboard.csv"
    write_header = not lb_path.exists()
    with open(lb_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "graph_key", "graph_name", "module", "algorithm",
                "datetime", "seed",
                "n", "m", "maxdeg", "avgdeg", "comps", "faces", "euler_ok",
                "colors_used", "assignments", "backtracks", "conflicts",
            ])
        writer.writerow([
            graph_key, graph_name, graph_module, algo_name, dt_stamp, seed,
            stats["n"], stats["m"], stats["maxdeg"], stats["avgdeg"],
            stats["comps"], stats["faces"], stats["euler_ok"],
            num_colors,
            run_meta["assignments"], run_meta["backtracks"],
            run_meta["conflicts"],
        ])
    print(f"[OK] Leaderboard -> {lb_path}")
    print("Done.")


if __name__ == "__main__":
    main()
