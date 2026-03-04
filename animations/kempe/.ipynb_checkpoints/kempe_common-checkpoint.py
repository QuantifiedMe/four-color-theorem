#!/usr/bin/env python3
# ============================================================================
# kempe_common.py  —  Shared utilities for Kempe / Heawood animation modules
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
# This module contains shared constants, graph construction functions, and
# animation utilities used by both kempe_proof.py and heawood_counterexample.py.
#
# Contents:
#   - File path constants for video output
#   - Visual style constants (colors, sizes, fonts)
#   - Render settings (1:1 square, high quality)
#   - Manim configuration
#   - Post-render file copy utility
#   - Graph construction helpers (make_manim_graph, color/uncolor/flash)
#   - Kempe chain computation and swap logic
#   - Header and narration HUD builders
#   - Hand-crafted graph definitions (degree 3, 4, 5-success, 5-failure)
#
# ============================================================================

from manim import *
import networkx as nx
import numpy as np
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================================
# FILE PATHS — imported from centralized config.py
# ============================================================================
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
try:
    from config import (
        KEMPE_VIDEO_DIR, MANIM_MEDIA_DIR as _MANIM_MEDIA_DIR,
        PASTEL_HEX_COLORS, StyleKempe, RenderKempe, C_BLUE, C_PURPLE,
        C_YELLOW, C_PINK, COLOR_NAMES,
    )
    VIDEO_OUTPUT_DIR = str(KEMPE_VIDEO_DIR)
    MANIM_MEDIA_DIR  = str(_MANIM_MEDIA_DIR)
except ImportError:
    VIDEO_OUTPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\Created Videos\KempeProofVideos"
    )
    MANIM_MEDIA_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output"
    )


# ============================================================================
# VISUAL STYLE CONSTANTS
# ============================================================================

PASTEL_HEX_COLORS = [
    "#8AAFFF",  # Color 0 — soft blue
    "#D5B1FF",  # Color 1 — soft purple
    "#FFDA8A",  # Color 2 — soft yellow
    "#FF8AAF",  # Color 3 — soft pink
    "#DA8AFF",  "#AFFF8A",  "#9F8AFF",  "#FF8AEA",
]

C_BLUE   = 0
C_PURPLE = 1
C_YELLOW = 2
C_PINK   = 3

COLOR_NAMES = {0: "Blue", 1: "Purple", 2: "Yellow", 3: "Pink"}

EDGE_STROKE_WIDTH   = 5
EDGE_COLOR           = BLACK
KEMPE_CHAIN_WIDTH    = 9
KEMPE_GLOW_WIDTH     = 14

NODE_RADIUS          = 0.30
NODE_STROKE_WIDTH    = 3
TARGET_NODE_RADIUS   = 0.38

LABEL_FONT_SIZE      = 24
TITLE_FONT_SIZE      = 36
SUBTITLE_FONT_SIZE   = 24

NARRATION_FONT_SIZE  = 26
NARR_COLOR           = BLACK
NARR_ALERT_COLOR     = "#CC0000"
NARR_SUCCESS_COLOR   = "#007700"
NARR_EMPHASIS_COLOR  = BLACK

SPEED = 1.5


# ============================================================================
# RENDER SETTINGS  (1:1 square, high quality)
# ============================================================================

PIXEL_WIDTH  = 1920
PIXEL_HEIGHT = 1920
FRAME_RATE   = 30
FRAME_HEIGHT = 8.0
FRAME_WIDTH  = FRAME_HEIGHT * (PIXEL_WIDTH / PIXEL_HEIGHT)

CONTENT_CENTER_Y = -0.3
HEADER_BOTTOM_Y  =  2.8


# ============================================================================
# MANIM CONFIGURATION
# ============================================================================

config.pixel_width  = PIXEL_WIDTH
config.pixel_height = PIXEL_HEIGHT
config.frame_rate   = FRAME_RATE
config.frame_height = FRAME_HEIGHT
config.frame_width  = FRAME_WIDTH
config.media_dir    = MANIM_MEDIA_DIR


# ============================================================================
# POST-RENDER UTILITY
# ============================================================================

def copy_to_output(scene_name):
    """Copy the rendered video to VIDEO_OUTPUT_DIR for easy access."""
    src_root = Path(MANIM_MEDIA_DIR)
    dst_dir  = Path(VIDEO_OUTPUT_DIR)
    dst_dir.mkdir(parents=True, exist_ok=True)

    candidates = list(src_root.rglob(f"{scene_name}*.mp4"))
    if not candidates:
        print(f"  [copy] No .mp4 found for {scene_name} under {src_root}")
        return

    best = max(candidates, key=lambda p: p.stat().st_mtime)
    dst  = dst_dir / best.name
    shutil.copy2(best, dst)
    print(f"  [copy] {best.name}  →  {dst_dir}")


# ============================================================================
# UTILITY: Build Manim graph from NetworkX + hand-placed positions
# ============================================================================

def make_manim_graph(G, pos, target_v=None):
    """Create a Manim Graph object with labeled vertices.

    The target vertex (the one being removed/reinserted by induction) is
    drawn slightly larger with a red border to distinguish it visually.
    """
    vertices = list(G.nodes())
    edges = list(G.edges())

    vertex_config = {}
    for v in vertices:
        vertex_config[v] = {
            "radius": TARGET_NODE_RADIUS if v == target_v else NODE_RADIUS,
            "stroke_width": NODE_STROKE_WIDTH,
            "stroke_color": RED if v == target_v else BLACK,
            "fill_color": WHITE,
            "fill_opacity": 1.0,
        }

    g = Graph(
        vertices, edges,
        layout=pos,
        edge_config={"stroke_width": EDGE_STROKE_WIDTH, "color": EDGE_COLOR},
        vertex_config=vertex_config,
    )

    labels = VGroup(*[
        Text(str(v), color=BLACK, font_size=LABEL_FONT_SIZE)
        .move_to(g.vertices[v].get_center())
        .set_z_index(10)
        for v in vertices
    ])

    return g, labels


def color_vertex(scene, g, v, color_idx, run_time=0.3):
    """Animate coloring a vertex with the given palette index."""
    hex_c = PASTEL_HEX_COLORS[color_idx % len(PASTEL_HEX_COLORS)]
    scene.play(
        g.vertices[v].animate.set_fill(hex_c, opacity=1.0),
        run_time=run_time * SPEED,
    )


def uncolor_vertex(scene, g, v, run_time=0.2):
    """Animate reverting a vertex to white (uncolored)."""
    scene.play(
        g.vertices[v].animate.set_fill(WHITE, opacity=1.0),
        run_time=run_time * SPEED,
    )


def flash_vertex(scene, g, v, color=RED, run_time=0.4):
    """Flash a vertex with a radial burst for emphasis."""
    scene.play(
        Flash(g.vertices[v], color=color, flash_radius=0.5),
        run_time=run_time * SPEED,
    )


# ============================================================================
# UTILITY: Kempe chain computation
# ============================================================================

def find_kempe_chain(G, coloring, start_v, c1, c2):
    """Return the connected component of the {c1, c2}-subgraph containing
    start_v.  This is the Kempe chain used for color swapping."""
    assert coloring[start_v] in (c1, c2), \
        f"start_v={start_v} has color {coloring[start_v]}, expected {c1} or {c2}"
    chain_vertices = {v for v in G.nodes() if coloring.get(v) in (c1, c2)}
    sub = G.subgraph(chain_vertices)
    for comp in nx.connected_components(sub):
        if start_v in comp:
            return comp
    return {start_v}


def swap_kempe_chain(coloring, chain, c1, c2):
    """Swap colors c1 ↔ c2 for every vertex in the chain.

    Returns a list of (vertex, old_color, new_color) triples for animation.
    """
    swaps = []
    for v in chain:
        old = coloring[v]
        if old == c1:
            coloring[v] = c2
            swaps.append((v, old, c2))
        elif old == c2:
            coloring[v] = c1
            swaps.append((v, old, c1))
    return swaps


def kempe_chain_edges(G, chain):
    """Return all edges of G whose both endpoints lie in the chain."""
    chain_set = set(chain)
    return [(u, v) for u, v in G.edges() if u in chain_set and v in chain_set]


# ============================================================================
# UTILITY: Header panel (reusable HUD across all scenes)
# ============================================================================

def build_header(title_str, subtitle_str, info_lines=None):
    """Build a header bar with title (left) and info panel (right),
    separated by a vertical rule and underlined by a horizontal rule."""
    EDGE_BUFF = 0.15

    title = Text(title_str, font_size=TITLE_FONT_SIZE, color=BLACK)
    subtitle = Text(subtitle_str, font_size=SUBTITLE_FONT_SIZE, color=BLACK)
    block1 = VGroup(title, subtitle).arrange(DOWN, aligned_edge=LEFT, buff=0.08)

    if info_lines:
        info_texts = [Text(l, font_size=20, color=BLACK) for l in info_lines]
        block2 = VGroup(*info_texts).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
    else:
        block2 = VGroup(Text(" ", font_size=20, color=BLACK))

    block1.to_edge(UP, buff=EDGE_BUFF).to_edge(LEFT, buff=EDGE_BUFF)
    block2.to_edge(UP, buff=EDGE_BUFF).to_edge(RIGHT, buff=EDGE_BUFF + 0.3)
    block2.align_to(block1, UP)

    header_row = VGroup(block1, block2)
    sep_x = (block1.get_right()[0] + block2.get_left()[0]) / 2
    h_top = header_row.get_top()[1] + 0.06
    h_bot = header_row.get_bottom()[1] - 0.06

    sep = Line(start=np.array([sep_x, h_top, 0]),
               end=np.array([sep_x, h_bot, 0]),
               stroke_width=2, color=GRAY_B)

    rule_y = h_bot - 0.06
    rule = Line(
        start=np.array([-(config.frame_width / 2) + EDGE_BUFF, rule_y, 0]),
        end=np.array([(config.frame_width / 2) - EDGE_BUFF, rule_y, 0]),
        stroke_width=3, color=BLACK,
    )

    return VGroup(header_row, sep, rule)


# ============================================================================
# UTILITY: Narration text (bottom overlay)
# ============================================================================

def show_narration(scene, text_str, position=DOWN, buff=0.25,
                   font_size=None, color=None, hold=1.0,
                   fade_in=0.4, fade_out=0.3):
    """Display narration text, hold briefly, then fade out."""
    fs = font_size or NARRATION_FONT_SIZE
    c  = color or NARR_COLOR
    txt = Text(text_str, font_size=fs, color=c).to_edge(position, buff=buff)
    max_w = config.frame_width - 0.6
    if txt.width > max_w:
        txt.scale(max_w / txt.width)
    scene.play(FadeIn(txt), run_time=fade_in * SPEED)
    scene.wait(hold * SPEED)
    scene.play(FadeOut(txt), run_time=fade_out * SPEED)
    return txt


def add_persistent_narration(scene, text_str, position=DOWN, buff=0.25,
                             font_size=None, color=None):
    """Add narration that stays on screen until explicitly removed.
    Returns the Text mobject for later FadeOut."""
    fs = font_size or NARRATION_FONT_SIZE
    c  = color or NARR_COLOR
    txt = Text(text_str, font_size=fs, color=c).to_edge(position, buff=buff)
    max_w = config.frame_width - 0.6
    if txt.width > max_w:
        txt.scale(max_w / txt.width)
    scene.play(FadeIn(txt), run_time=0.4 * SPEED)
    return txt


# ============================================================================
# HAND-CRAFTED GRAPHS
# ============================================================================

def build_degree3_graph():
    """Triangulation with a degree-3 interior vertex (v0)."""
    G = nx.Graph()
    G.add_edges_from([
        (0, 1), (0, 2), (0, 3),
        (1, 2), (2, 3), (3, 1),
        (1, 4), (2, 4),
        (1, 5), (3, 5),
        (2, 6), (3, 6),
        (4, 5), (5, 6), (4, 6),
    ])

    pos = {
        0: np.array([ 0.0, -0.2,  0.0]),
        1: np.array([-1.9,  1.1,  0.0]),
        2: np.array([ 1.9,  1.1,  0.0]),
        3: np.array([ 0.0, -1.8,  0.0]),
        4: np.array([ 0.0,  3.2,  0.0]),
        5: np.array([-3.4, -1.8,  0.0]),
        6: np.array([ 3.4, -1.8,  0.0]),
    }
    return G, pos, 0


def build_degree4_graph():
    """Triangulation with a degree-4 interior vertex (v0)."""
    G = nx.Graph()
    G.add_edges_from([
        (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 2), (2, 3), (3, 4), (4, 1),
        (1, 5), (2, 5), (2, 6), (3, 6),
        (3, 7), (4, 7), (4, 8), (1, 8),
        (5, 6), (6, 7), (7, 8), (8, 5),
    ])

    s = 1.6
    d = 3.2 * 0.707
    pos = {
        0: np.array([0.0, 0.0, 0.0]),
        1: np.array([0.0,  s,  0.0]),
        2: np.array([s,   0.0, 0.0]),
        3: np.array([0.0, -s,  0.0]),
        4: np.array([-s,  0.0, 0.0]),
        5: np.array([ d,  d, 0.0]),
        6: np.array([ d, -d, 0.0]),
        7: np.array([-d, -d, 0.0]),
        8: np.array([-d,  d, 0.0]),
    }
    return G, pos, 0


def build_degree5_success_graph():
    """Degree-5 graph where Kempe's chain swap succeeds.

    The {Purple, Pink} chain from v2 yields {v2, v7}, which is isolated
    from v5.  Swapping frees Purple for v0.
    """
    G = nx.Graph()
    for i in range(1, 6):
        G.add_edge(0, i)
    for i in range(1, 6):
        G.add_edge(i, (i % 5) + 1)
    for ov, (a, b) in {6:(1,2), 7:(2,3), 8:(3,4), 9:(4,5), 10:(5,1)}.items():
        G.add_edge(ov, a)
        G.add_edge(ov, b)

    inner_r = 1.8
    outer_r = 3.4
    pos = {0: np.array([0.0, 0.0, 0.0])}
    for i in range(5):
        angle = np.pi / 2 + 2 * np.pi * i / 5
        pos[i + 1] = np.array([inner_r * np.cos(angle),
                                inner_r * np.sin(angle), 0.0])
        pos[i + 6] = np.array([outer_r * np.cos(angle + np.pi / 5),
                                outer_r * np.sin(angle + np.pi / 5), 0.0])

    initial_coloring = {
        1: C_BLUE,   2: C_PURPLE,  3: C_YELLOW,
        4: C_BLUE,   5: C_PINK,
        6: C_YELLOW, 7: C_PINK,    8: C_PURPLE,
        9: C_YELLOW, 10: C_PURPLE,
    }
    return G, pos, 0, initial_coloring


def build_degree5_failure_graph():
    """Degree-5 graph demonstrating Kempe's error (Heawood 1890).

    Two Kempe chains interfere:
      K(Blue, Yellow) from v1 = {v1, v3, v4, v6, v7, v10} — connects
          through the exterior, reaching v4.
      K(Blue, Pink)   from v4 = {v1, v4, v5} — connects through the ring,
          reaching v1.
    Both chains connect their targets.  Shared vertices: v1, v4.
    Swapping K(Blue, Yellow) turns v4 from Blue to Yellow, destroying
    the K(Blue, Pink) chain.
    """
    G = nx.Graph()
    for i in range(1, 6):
        G.add_edge(0, i)
    for i in range(1, 6):
        G.add_edge(i, (i % 5) + 1)

    G.add_edges_from([(1, 6), (6, 2), (6, 7), (7, 2), (7, 3)])
    G.add_edges_from([(3, 8), (8, 4)])
    G.add_edges_from([(4, 9), (9, 5)])
    G.add_edges_from([(5, 10), (10, 1)])

    inner_r = 1.8
    ext_r   = 3.4

    ring_angles = [np.pi / 2 - 2 * np.pi * i / 5 for i in range(5)]

    pos = {0: np.array([0.0, 0.0, 0.0])}
    for i in range(5):
        a = ring_angles[i]
        pos[i + 1] = np.array([inner_r * np.cos(a),
                                inner_r * np.sin(a), 0.0])

    for i in range(5):
        a1 = ring_angles[i]
        a2 = ring_angles[(i + 1) % 5]
        diff = (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
        mid = a1 + diff / 2
        pos[i + 6] = np.array([ext_r * np.cos(mid),
                                ext_r * np.sin(mid), 0.0])

    coloring = {
        1: C_BLUE,    2: C_PURPLE,  3: C_YELLOW,
        4: C_BLUE,    5: C_PINK,
        6: C_YELLOW,  7: C_BLUE,    8: C_PURPLE,
        9: C_PURPLE,  10: C_YELLOW,
    }
    return G, pos, 0, coloring