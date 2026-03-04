#!/usr/bin/env python3
# ============================================================================
# kempe_module1.py  —  Module 1: Kempe's Almost-Proof
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
# This module animates the historical foundation of the Four-Color Theorem
# proof: Alfred Kempe's 1879 "proof" and the fatal flaw discovered by Percy
# Heawood in 1890.  It introduces the technique of Kempe chains, which
# underpins every subsequent proof of the theorem.
#
# The module consists of three self-contained Manim scenes, plus a combined
# scene that renders all three as a single continuous video:
#
#   Scene 1 — KempeEasyCases
#       The inductive argument for vertices of degree 3 and 4.  A target
#       vertex is removed from a small triangulation, the reduced graph
#       is colored by "induction," and the vertex is reinserted.  Because
#       only 3 (or 4, with a pair sharing a color) neighbors exist, a free
#       color is always available.
#
#   Scene 2 — KempeChainSuccess
#       The degree-5 case where Kempe's chain argument works.  A vertex v
#       of degree 5 has all four colors on its ring.  We compute the Kempe
#       chain K(Purple, Pink) from v2, show it does NOT reach v5, swap
#       colors, and assign the freed color to v0.
#
#   Scene 3 — KempeChainFailure
#       Heawood's 1890 counterexample.  Two Kempe chains both connect
#       their targets simultaneously.  Swapping one chain destroys the
#       other.  This is the dramatic climax of Module 1.
#
#   Combined — KempeModule1Complete
#       Renders all three scenes sequentially as a single video file,
#       suitable for uninterrupted presentation playback.
#
# ============================================================================
# USAGE
# ============================================================================
#
#   Individual scenes (for testing / editing):
#     manim -qh kempe_module1.py KempeEasyCases
#     manim -qh kempe_module1.py KempeChainSuccess
#     manim -qh kempe_module1.py KempeChainFailure
#
#   All scenes as one continuous video:
#     manim -qh kempe_module1.py KempeModule1Complete
#
#   All scenes (renders each separately):
#     manim -qh kempe_module1.py
#
# ============================================================================
# REFERENCES
# ============================================================================
#
#   [1] A. B. Kempe, "On the Geographical Problem of the Four Colours,"
#       Amer. J. Math., vol. 2, no. 3, pp. 193-200, 1879.
#   [2] P. J. Heawood, "Map-Colour Theorem," Quart. J. Pure Appl. Math.,
#       vol. 24, pp. 332-338, 1890.
#   [3] K. Appel and W. Haken, "Every Planar Map is Four Colorable,
#       Part I: Discharging," Illinois J. Math., vol. 21, 1977.
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

# Narration / HUD text — sized for classroom projector visibility.
# All narration uses fully saturated colors (never pastels) for legibility.
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

# Header occupies top ~1.5 units; narration occupies bottom ~0.8 units.
# Graph content is placed within this bounded interior region.
CONTENT_CENTER_Y = -0.3
HEADER_BOTTOM_Y  =  2.8


# ============================================================================
# MANIM CONFIGURATION
# ============================================================================
# Direct Manim's media output to the project's Video Output folder so that
# rendered files appear in the expected location rather than the default
# ./media directory adjacent to the script.
# ============================================================================

config.pixel_width  = PIXEL_WIDTH
config.pixel_height = PIXEL_HEIGHT
config.frame_rate   = FRAME_RATE
config.frame_height = FRAME_HEIGHT
config.frame_width  = FRAME_WIDTH
config.media_dir    = MANIM_MEDIA_DIR


# ============================================================================
# POST-RENDER UTILITY: copy finished videos to presentation folder
# ============================================================================

def copy_to_output(scene_name):
    """Copy the rendered video to VIDEO_OUTPUT_DIR for easy access.

    Searches MANIM_MEDIA_DIR for the most recently created .mp4 matching
    the scene name and copies it to the presentation output folder.
    """
    src_root = Path(MANIM_MEDIA_DIR)
    dst_dir  = Path(VIDEO_OUTPUT_DIR)
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Find all mp4 files that match the scene name
    candidates = list(src_root.rglob(f"{scene_name}*.mp4"))
    if not candidates:
        print(f"  [copy] No .mp4 found for {scene_name} under {src_root}")
        return

    # Pick the most recently modified file
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
# Layout philosophy: inner (ring) vertices are placed at a moderate radius
# so that edges to the center vertex have room to breathe.  Outer vertices
# are pushed far enough that their edges to the ring do not cross through
# the interior of the graph.
# ============================================================================

def build_degree3_graph():
    """Triangulation with a degree-3 interior vertex (v0).

    Vertex positions are arranged so that the outer edges (v4-v5, v4-v6)
    pass well clear of the inner edges (v0-v1, v0-v2).  The key is
    widening v1/v2 horizontally and lowering v0 to create separation.
    """
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

    Exterior vertex positions are computed with proper angular midpoints
    so that v10 (between v5 and v1) mirrors v6 (between v1 and v2)
    symmetrically across the vertical axis.
    """
    G = nx.Graph()
    for i in range(1, 6):
        G.add_edge(0, i)
    for i in range(1, 6):
        G.add_edge(i, (i % 5) + 1)

    # Exterior edges forming the {Blue, Yellow} chain path
    G.add_edges_from([(1, 6), (6, 2), (6, 7), (7, 2), (7, 3)])
    # Triangulation fill vertices
    G.add_edges_from([(3, 8), (8, 4)])
    G.add_edges_from([(4, 9), (9, 5)])
    G.add_edges_from([(5, 10), (10, 1)])

    # Ring vertices: placed clockwise starting from the top
    inner_r = 1.8
    ext_r   = 3.4

    ring_angles = [np.pi / 2 - 2 * np.pi * i / 5 for i in range(5)]

    pos = {0: np.array([0.0, 0.0, 0.0])}
    for i in range(5):
        a = ring_angles[i]
        pos[i + 1] = np.array([inner_r * np.cos(a),
                                inner_r * np.sin(a), 0.0])

    # Exterior vertices: placed at the angular midpoint between adjacent
    # ring vertices, using the SHORT arc so that the midpoint stays on
    # the correct side of the pentagon.
    for i in range(5):
        a1 = ring_angles[i]
        a2 = ring_angles[(i + 1) % 5]
        # Compute shortest-arc midpoint
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


# ============================================================================
# SCENE 1: KempeEasyCases
# ============================================================================

class KempeEasyCases(Scene):
    """Degree-3 and degree-4 induction cases — where Kempe's proof works.

    Demonstrates that when a vertex has at most 4 neighbors, the inductive
    step is straightforward: remove the vertex, color the rest, reinsert,
    and a free color is always available (possibly after a simple swap).
    """

    def construct(self):
        self.camera.background_color = WHITE
        self.next_section("Degree-3 Case")

        # ======================== ACT I: DEGREE 3 ========================
        header = build_header(
            "Kempe's Proof",
            "Step 1: The Easy Cases",
            info_lines=["Degree-3 vertex", "removal & recoloring"],
        )
        self.add(header)

        G3, pos3, target = build_degree3_graph()
        g3, lbl3 = make_manim_graph(G3, pos3, target_v=target)
        VGroup(g3, lbl3).move_to(np.array([0.0, CONTENT_CENTER_Y, 0.0]))

        self.play(Create(g3), run_time=1.5)
        self.add(lbl3)
        self.bring_to_front(lbl3)

        narr = add_persistent_narration(
            self, "Vertex 0 has degree 3.  Remove it by induction.",
        )
        self.wait(1.5 * SPEED)

        self.play(
            g3.vertices[0].animate.set_stroke(RED, width=6),
            run_time=0.5 * SPEED,
        )
        self.wait(0.5 * SPEED)

        # Fade out vertex 0 and its incident edges
        edges_to_fade = [(u, v) for u, v in G3.edges() if u == 0 or v == 0]
        fade_anims = [FadeOut(g3.vertices[0]), FadeOut(lbl3[0])]
        for e in edges_to_fade:
            key = e if e in g3.edges else (e[1], e[0])
            if key in g3.edges:
                fade_anims.append(FadeOut(g3.edges[key]))
        self.play(*fade_anims, run_time=0.8 * SPEED)
        self.play(FadeOut(narr), run_time=0.3)

        narr2 = add_persistent_narration(
            self, "Color the reduced graph by induction (at most 4 colors).",
        )
        self.wait(0.8 * SPEED)

        for v, c in [(1, C_BLUE), (2, C_PURPLE), (3, C_YELLOW),
                      (4, C_PINK), (5, C_BLUE), (6, C_YELLOW)]:
            color_vertex(self, g3, v, c, run_time=0.25)

        self.play(FadeOut(narr2), run_time=0.3)
        self.wait(0.5 * SPEED)

        narr3 = add_persistent_narration(
            self,
            "Reinsert v0.  Neighbors use Blue, Purple, Yellow.  Pink is free!",
            color=NARR_SUCCESS_COLOR,
        )

        fade_in_anims = [FadeIn(g3.vertices[0]), FadeIn(lbl3[0])]
        for e in edges_to_fade:
            key = e if e in g3.edges else (e[1], e[0])
            if key in g3.edges:
                fade_in_anims.append(FadeIn(g3.edges[key]))
        self.play(*fade_in_anims, run_time=0.8 * SPEED)
        self.wait(1.0 * SPEED)

        color_vertex(self, g3, 0, C_PINK, run_time=0.5)
        flash_vertex(self, g3, 0, color=GREEN)
        self.play(FadeOut(narr3), run_time=0.3)
        self.wait(1.0 * SPEED)

        # ======================== ACT II: DEGREE 4 ========================
        self.next_section("Degree-4 Case")
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.8)

        header2 = build_header(
            "Kempe's Proof", "Step 1: The Easy Cases",
            info_lines=["Degree-4 vertex", "removal & recoloring"],
        )
        self.add(header2)

        G4, pos4, target4 = build_degree4_graph()
        g4, lbl4 = make_manim_graph(G4, pos4, target_v=target4)
        VGroup(g4, lbl4).move_to(np.array([0.0, CONTENT_CENTER_Y, 0.0]))

        self.play(Create(g4), run_time=1.5)
        self.add(lbl4)
        self.bring_to_front(lbl4)

        narr4 = add_persistent_narration(
            self, "Vertex 0 has degree 4.  Remove it by induction.",
        )
        self.wait(1.0 * SPEED)
        self.play(g4.vertices[0].animate.set_stroke(RED, width=6),
                  run_time=0.5 * SPEED)

        edges_to_fade4 = [(u, v) for u, v in G4.edges() if u == 0 or v == 0]
        fade4 = [FadeOut(g4.vertices[0]), FadeOut(lbl4[0])]
        for e in edges_to_fade4:
            key = e if e in g4.edges else (e[1], e[0])
            if key in g4.edges:
                fade4.append(FadeOut(g4.edges[key]))
        self.play(*fade4, run_time=0.8 * SPEED)
        self.play(FadeOut(narr4), run_time=0.3)

        narr5 = add_persistent_narration(
            self, "Color by induction.  4 neighbors may use all 4 colors...",
        )

        for v, c in [(1, C_BLUE), (2, C_PURPLE), (3, C_YELLOW), (4, C_PINK),
                      (5, C_YELLOW), (6, C_PINK), (7, C_BLUE), (8, C_PURPLE)]:
            color_vertex(self, g4, v, c, run_time=0.2)

        self.play(FadeOut(narr5), run_time=0.3)

        narr6 = add_persistent_narration(
            self, "v1 and v3 are non-adjacent.  Kempe chain swap frees a color!",
        )
        self.wait(1.5 * SPEED)

        fin4 = [FadeIn(g4.vertices[0]), FadeIn(lbl4[0])]
        for e in edges_to_fade4:
            key = e if e in g4.edges else (e[1], e[0])
            if key in g4.edges:
                fin4.append(FadeIn(g4.edges[key]))
        self.play(*fin4, run_time=0.8 * SPEED)
        self.play(FadeOut(narr6), run_time=0.3)

        narr7 = add_persistent_narration(
            self,
            "Swap Blue and Yellow on v1's chain.  Blue is now free for v0!",
            color=NARR_SUCCESS_COLOR,
        )
        color_vertex(self, g4, 1, C_YELLOW, run_time=0.4)
        self.wait(0.5 * SPEED)
        color_vertex(self, g4, 0, C_BLUE, run_time=0.5)
        flash_vertex(self, g4, 0, color=GREEN)
        self.play(FadeOut(narr7), run_time=0.3)

        show_narration(
            self,
            "Degree 4 or less always works.  The hard case is degree 5...",
            color=NARR_EMPHASIS_COLOR, hold=2.0,
        )
        self.wait(1.0 * SPEED)


# ============================================================================
# SCENE 2: KempeChainSuccess
# ============================================================================

class KempeChainSuccess(Scene):
    """Degree-5 case where the Kempe chain swap works.

    The {Purple, Pink} chain from v2 is an isolated component that does
    not reach v5, so the swap safely frees Purple for the target vertex.
    """

    def construct(self):
        self.camera.background_color = WHITE

        header = build_header(
            "Kempe's Proof", "Step 2: Degree 5 — Success",
            info_lines=["Kempe chain swap", "frees a color for v0"],
        )
        self.add(header)

        G, pos, target, init_coloring = build_degree5_success_graph()
        g, lbl = make_manim_graph(G, pos, target_v=target)
        VGroup(g, lbl).scale(0.78).move_to(
            np.array([0.0, CONTENT_CENTER_Y, 0.0])
        )

        self.play(Create(g), run_time=1.5)
        self.add(lbl)
        self.bring_to_front(lbl)
        self.wait(0.5 * SPEED)

        # Color all vertices except v0
        narr = add_persistent_narration(
            self, "Remove v0, color by induction, reinsert.  All 4 colors on ring!",
        )
        for v, c in sorted(init_coloring.items()):
            color_vertex(self, g, v, c, run_time=0.15)
        self.wait(1.0 * SPEED)
        self.play(FadeOut(narr), run_time=0.3)

        # Highlight the shared-color pair
        narr2 = add_persistent_narration(
            self, "v1 and v4 both have Blue — and they're non-adjacent!",
        )
        self.play(
            g.vertices[1].animate.set_stroke(YELLOW, width=6),
            g.vertices[4].animate.set_stroke(YELLOW, width=6),
            run_time=0.5 * SPEED,
        )
        self.wait(1.5 * SPEED)
        self.play(
            g.vertices[1].animate.set_stroke(BLACK, width=NODE_STROKE_WIDTH),
            g.vertices[4].animate.set_stroke(BLACK, width=NODE_STROKE_WIDTH),
            run_time=0.3 * SPEED,
        )
        self.play(FadeOut(narr2), run_time=0.3)

        # Compute and display the Kempe chain
        coloring = dict(init_coloring)
        chain = find_kempe_chain(G, coloring, 2, C_PURPLE, C_PINK)
        chain_edges = kempe_chain_edges(G, chain)

        narr3 = add_persistent_narration(
            self, "Kempe chain {Purple, Pink} from v2.  Does it reach v5?",
        )
        for v in chain:
            self.play(g.vertices[v].animate.set_stroke(YELLOW, width=6),
                      run_time=0.2 * SPEED)

        glow_lines = VGroup()
        for u, v in chain_edges:
            s, e = g.vertices[u].get_center(), g.vertices[v].get_center()
            glow_lines.add(
                Line(s, e, stroke_width=KEMPE_GLOW_WIDTH,
                     color=YELLOW, stroke_opacity=0.4).set_z_index(-1),
                Line(s, e, stroke_width=KEMPE_CHAIN_WIDTH,
                     color=ORANGE).set_z_index(2),
            )
        if glow_lines:
            self.play(Create(glow_lines), run_time=0.8 * SPEED)
        self.bring_to_front(lbl)
        self.wait(1.0 * SPEED)
        self.play(FadeOut(narr3), run_time=0.3)

        chain_str = ", ".join("v" + str(v) for v in sorted(chain))
        narr4 = add_persistent_narration(
            self,
            f"NO!  Chain = {{{chain_str}}} — v5 is in a separate component.",
            color=NARR_SUCCESS_COLOR,
        )
        self.wait(1.5 * SPEED)
        self.play(FadeOut(narr4), run_time=0.3)

        # Perform the swap
        narr5 = add_persistent_narration(
            self, "Swap Purple and Pink along the chain.  v2 becomes Pink.",
        )
        swaps = swap_kempe_chain(coloring, chain, C_PURPLE, C_PINK)
        for v_sw, old_c, new_c in swaps:
            color_vertex(self, g, v_sw, new_c, run_time=0.3)
        self.play(FadeOut(glow_lines), run_time=0.5)
        for v in chain:
            g.vertices[v].set_stroke(BLACK, width=NODE_STROKE_WIDTH)
        self.wait(0.8 * SPEED)
        self.play(FadeOut(narr5), run_time=0.3)

        # Assign the freed color to v0
        narr6 = add_persistent_narration(
            self,
            "Ring: Blue, Pink, Yellow, Blue, Pink — Purple is free for v0!",
            color=NARR_SUCCESS_COLOR,
        )
        color_vertex(self, g, 0, C_PURPLE, run_time=0.6)
        flash_vertex(self, g, 0, color=GREEN)
        self.wait(1.0 * SPEED)
        self.play(FadeOut(narr6), run_time=0.3)

        show_narration(
            self,
            "Kempe's chain argument succeeds here.  But not always...",
            color=NARR_EMPHASIS_COLOR, hold=2.5,
        )
        self.wait(1.0 * SPEED)


# ============================================================================
# SCENE 3: KempeChainFailure
# ============================================================================

class KempeChainFailure(Scene):
    """Heawood's 1890 counterexample — two Kempe chains interfere.

    This scene reveals the flaw in Kempe's proof.  When the degree-5
    vertex has all four colors on its ring and two different Kempe chains
    share vertices, swapping one chain destroys the color structure that
    the other chain depends on.
    """

    def construct(self):
        self.camera.background_color = WHITE

        header = build_header(
            "Kempe's Error", "Heawood's Counterexample (1890)",
            info_lines=["Two chains interfere", "Swap scrambles the other"],
        )
        self.add(header)

        G, pos, target, init_coloring = build_degree5_failure_graph()
        g, lbl = make_manim_graph(G, pos, target_v=target)
        VGroup(g, lbl).scale(0.78).move_to(
            np.array([0.0, CONTENT_CENTER_Y, 0.0])
        )

        self.play(Create(g), run_time=1.5)
        self.add(lbl)
        self.bring_to_front(lbl)

        # Color all vertices except v0
        narr = add_persistent_narration(
            self, "Degree-5 vertex v0.  Ring colored with all 4 colors.",
        )
        for v, c in sorted(init_coloring.items()):
            color_vertex(self, g, v, c, run_time=0.12)
        self.wait(1.0 * SPEED)
        self.play(FadeOut(narr), run_time=0.3)

        # Highlight the shared-color pair
        narr2 = add_persistent_narration(
            self, "v1 and v4 both have Blue.  Non-adjacent — try Kempe chains!",
        )
        self.play(
            g.vertices[1].animate.set_stroke(YELLOW, width=6),
            g.vertices[4].animate.set_stroke(YELLOW, width=6),
            run_time=0.5 * SPEED,
        )
        self.wait(1.5 * SPEED)
        self.play(FadeOut(narr2), run_time=0.3)

        # Chain 1: {Blue, Yellow} from v1
        coloring = dict(init_coloring)
        chain_bg = find_kempe_chain(G, coloring, 1, C_BLUE, C_YELLOW)
        chain_bg_edges = kempe_chain_edges(G, chain_bg)

        narr3 = add_persistent_narration(
            self, "Chain 1: {Blue, Yellow} from v1...",
        )
        chain1_lines = VGroup()
        for u, v in chain_bg_edges:
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
        self.play(FadeOut(narr3), run_time=0.3)

        chain_str = ", ".join("v" + str(v) for v in sorted(chain_bg))
        narr4 = add_persistent_narration(
            self,
            f"Reaches v3 AND v4!  Chain = {{{chain_str}}}",
            color=NARR_ALERT_COLOR,
        )
        flash_vertex(self, g, 3, color=RED)
        flash_vertex(self, g, 4, color=RED)
        self.wait(1.5 * SPEED)
        self.play(FadeOut(narr4), run_time=0.3)

        # Chain 2: {Blue, Pink} from v4
        chain_bp = find_kempe_chain(G, coloring, 4, C_BLUE, C_PINK)
        chain_bp_edges = kempe_chain_edges(G, chain_bp)

        narr5 = add_persistent_narration(
            self, "Chain 2: {Blue, Pink} from v4...",
        )
        chain2_lines = VGroup()
        for u, v in chain_bp_edges:
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
        self.play(FadeOut(narr5), run_time=0.3)

        chain2_str = ", ".join("v" + str(v) for v in sorted(chain_bp))
        narr6 = add_persistent_narration(
            self,
            f"Reaches v5!  Chain = {{{chain2_str}}}",
            color=NARR_ALERT_COLOR,
        )
        flash_vertex(self, g, 5, color=RED)
        self.wait(1.5 * SPEED)
        self.play(FadeOut(narr6), run_time=0.3)

        # Both chains connect — the fatal overlap
        narr7 = add_persistent_narration(
            self, "BOTH chains connect!  They share v1 and v4 (both Blue).",
            color=NARR_ALERT_COLOR,
        )
        self.play(
            Flash(g.vertices[1], color=PURE_RED, flash_radius=0.6),
            Flash(g.vertices[4], color=PURE_RED, flash_radius=0.6),
            run_time=0.6 * SPEED,
        )
        self.wait(2.0 * SPEED)
        self.play(FadeOut(narr7), run_time=0.3)

        # Attempt the swap on Chain 1
        narr8 = add_persistent_narration(
            self, "Try swapping Chain 1 (Blue and Yellow) anyway...",
        )
        swaps1 = swap_kempe_chain(coloring, chain_bg, C_BLUE, C_YELLOW)
        for v_sw, old_c, new_c in swaps1:
            color_vertex(self, g, v_sw, new_c, run_time=0.25)
        self.play(FadeOut(chain1_lines), run_time=0.4)
        self.wait(0.8 * SPEED)
        self.play(FadeOut(narr8), run_time=0.3)

        # Reveal the destruction of Chain 2
        narr9 = add_persistent_narration(
            self, "v4 changed Blue to Yellow!  No longer in {Blue, Pink}!",
            color=NARR_ALERT_COLOR,
        )
        self.play(
            Flash(g.vertices[4], color=PURE_RED, flash_radius=0.6),
            run_time=0.5 * SPEED,
        )
        self.play(
            chain2_lines.animate.set_color(RED).set_stroke(opacity=0.5),
            run_time=0.6 * SPEED,
        )
        self.wait(1.0 * SPEED)

        center = g.vertices[0].get_center()
        xs = 0.5
        x_mark = VGroup(
            Line(center + LEFT*xs + UP*xs, center + RIGHT*xs + DOWN*xs,
                 stroke_width=8, color=RED),
            Line(center + RIGHT*xs + UP*xs, center + LEFT*xs + DOWN*xs,
                 stroke_width=8, color=RED),
        ).set_z_index(20)
        self.play(Create(x_mark), run_time=0.5 * SPEED)
        self.wait(1.0 * SPEED)
        self.play(FadeOut(narr9), FadeOut(chain2_lines), run_time=0.4)

        narr10 = add_persistent_narration(
            self, "Ring: Yellow, Purple, Blue, Yellow, Pink — still all 4 colors!",
            color=NARR_ALERT_COLOR,
        )
        self.wait(1.5 * SPEED)
        self.play(FadeOut(narr10), run_time=0.3)

        narr11 = add_persistent_narration(
            self, "Chain 2 is destroyed — no way to free Blue for v0!",
            color=NARR_ALERT_COLOR,
        )
        self.wait(2.0 * SPEED)
        self.play(FadeOut(narr11), FadeOut(x_mark), run_time=0.4)

        # Epilogue narration
        show_narration(self,
            "Heawood (1890): Kempe's argument is flawed at degree 5.",
            color=NARR_EMPHASIS_COLOR, hold=2.5)

        show_narration(self,
            "Consecutive chain swaps are NOT independent operations.",
            color=NARR_EMPHASIS_COLOR, hold=2.5)

        show_narration(self,
            "It took 86 more years to fix — Appel & Haken, 1976.",
            color=NARR_EMPHASIS_COLOR, hold=2.5)

        self.wait(1.0 * SPEED)


# ============================================================================
# COMBINED SCENE: KempeModule1Complete
# ============================================================================

class KempeModule1Complete(Scene):
    """All three Kempe scenes rendered as a single continuous video.

    Plays KempeEasyCases → KempeChainSuccess → KempeChainFailure with
    brief transitions between each act.  Suitable for uninterrupted
    presentation playback during the 45-minute presentation.
    """

    def construct(self):
        self.camera.background_color = WHITE

        # Act I: Easy Cases (degree 3 and 4)
        KempeEasyCases.construct(self)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
        self.wait(0.5)

        # Act II: Chain Success (degree 5, chain isolated)
        KempeChainSuccess.construct(self)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
        self.wait(0.5)

        # Act III: Chain Failure (Heawood's counterexample)
        KempeChainFailure.construct(self)


# ============================================================================
# MAIN — render individual scenes or run all at once
# ============================================================================

if __name__ == "__main__":
    import sys

    scenes = {
        "KempeEasyCases":       KempeEasyCases,
        "KempeChainSuccess":    KempeChainSuccess,
        "KempeChainFailure":    KempeChainFailure,
        "KempeModule1Complete": KempeModule1Complete,
    }

    if len(sys.argv) < 2:
        print("Module 1: Kempe's Almost-Proof")
        print("=" * 50)
        print("\nAvailable scenes:")
        for name in scenes:
            print(f"  manim -qh kempe_module1.py {name}")
        print(f"\nRender all individual scenes + combined video:")
        print(f"  manim -qh kempe_module1.py")
        sys.exit(0)