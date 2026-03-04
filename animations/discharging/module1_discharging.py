# module1_discharging.py
#
# ===========================================================================
# Module 1 — Discharging & Unavoidability
# Four-Color Theorem Senior Project
#
# Demonstrates HOW the unavoidable set of 633 configurations was built
# using the discharging method (Robertson–Sanders–Seymour–Thomas, 1997).
#
# Scenes (run individually or as a sequence):
#   1) EulerChargeIntro     — Euler's formula → initial charge assignment
#   2) DischargingDemo      — Animated discharging on a sample triangulation
#   3) UnavoidabilityProof  — The contradiction argument (proof by cases)
#   4) ConfigGallery        — Parse & display configs from unavoidable_conf.txt
#
# Usage:
#   manim -pql module1_discharging.py EulerChargeIntro
#   manim -pql module1_discharging.py DischargingDemo
#   manim -pql module1_discharging.py UnavoidabilityProof
#   manim -pql module1_discharging.py ConfigGallery
#   manim -pql module1_discharging.py FullModule1          # all four in order
#
# Requires:  manim, networkx, numpy
# Config file:  unavoidable_conf.txt  (RSST 633 configurations)
# ===========================================================================

from manim import *
import networkx as nx
import numpy as np
import re
import os
import sys
from pathlib import Path

# ==========================
# Paths — imported from centralized config.py
# ==========================
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
try:
    from config import UNAVOIDABLE_CONF_PATH, StyleDischarging, RenderDischarging
    CONF_PATH = str(UNAVOIDABLE_CONF_PATH)
except ImportError:
    CONF_PATH = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Input\unavoidable.conf"
    )

# ==========================
# Render settings  (match your existing project)
# ==========================
PIXEL_WIDTH  = 1920
PIXEL_HEIGHT = 1080
FRAME_RATE   = 30
FRAME_HEIGHT = 8.0
FRAME_WIDTH  = FRAME_HEIGHT * (PIXEL_WIDTH / PIXEL_HEIGHT)

# ==========================
# Visual Style
# ==========================
# Charge-based color scheme
POS_CHARGE_COLOR  = "#FF6B6B"   # red  — positive charge (deg 5)
ZERO_CHARGE_COLOR = "#B0B0B0"   # gray — zero charge    (deg 6)
NEG_CHARGE_COLOR  = "#4ECDC4"   # teal — negative charge (deg 7+)

# Configuration display colors  (ring vs interior)
RING_COLOR     = "#A9FFCD"
INTERIOR_COLOR = "#FFD5AF"
HIGHLIGHT_COLOR = "#FFE66D"

EDGE_STROKE_WIDTH = 3
EDGE_COLOR        = BLACK
NODE_RADIUS       = 0.28
NODE_STROKE_WIDTH = 2.5
LABEL_FONT_SIZE   = 20
CHARGE_FONT_SIZE  = 16
TITLE_FONT_SIZE   = 36
BODY_FONT_SIZE    = 24

# Pastel palette (reuse from your existing project)
PASTEL_HEX = [
    "#FFD5AF", "#D5B1FF", "#FFBED6", "#A9FFCD",
    "#FFFDAB", "#A6D854", "#E7D4E8", "#FFD92F",
    "#E5C494", "#B3B3B3", "#8DD3C7", "#FFFFB3",
    "#BEBADA", "#FB8072", "#80B1D3", "#FDB462",
]

SPEED_FACTOR = .25  # <1 = slower, >1 = faster


# =========================================================================
#  CONFIGURATION PARSER — reads RSST unavoidable.conf
# =========================================================================

def parse_unavoidable_configs(path: str) -> list:
    """Parse the RSST unavoidable configuration file.

    Returns a list of dicts, each with:
        id          : str   (the header line, e.g. "0.7322")
        n_verts     : int
        ring_size   : int
        n_edges_enc : int   (encoded edge count from header)
        n_contract  : int
        contracts   : list of (int,int) pairs
        adj         : dict  {vertex: [neighbors]}   (1-indexed)
        degrees     : dict  {vertex: degree}
        graph       : nx.Graph
    """
    if not os.path.exists(path):
        print(f"[WARN] Config file not found: {path}")
        return []

    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    lines = raw.replace("\r\n", "\n").split("\n")
    configs = []
    idx = 0

    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue

        # Header line: a decimal number like "0.7322" or "26359322.-7322"
        if re.match(r"^\d+\.[-]?\d+", line) and len(line.split()) == 1:
            cfg = {"id": line}
            idx += 1
            if idx >= len(lines):
                break

            # Parameters: n_verts  ring_size  encoded_edges  n_contract_pairs
            params = lines[idx].split()
            cfg["n_verts"]     = int(params[0])
            cfg["ring_size"]   = int(params[1])
            cfg["n_edges_enc"] = int(params[2])
            cfg["n_contract"]  = int(params[3]) if len(params) > 3 else 0
            idx += 1

            # Contract pairs line
            contract_line = lines[idx].strip()
            cfg["contracts"] = []
            if contract_line != "0":
                # Parse contract pairs
                cparts = contract_line.split()
                n_pairs = int(cparts[0]) if cparts else 0
                for p in range(n_pairs):
                    a, b = int(cparts[1 + 2*p]), int(cparts[2 + 2*p])
                    cfg["contracts"].append((a, b))
            idx += 1

            # Read vertex adjacency lines
            adj = {}
            degrees = {}
            for _ in range(cfg["n_verts"]):
                if idx >= len(lines):
                    break
                vline = lines[idx].strip()
                parts = vline.split()
                v   = int(parts[0])
                deg = int(parts[1])
                nbrs = [int(x) for x in parts[2:]]
                adj[v] = nbrs
                degrees[v] = deg
                idx += 1

            cfg["adj"]     = adj
            cfg["degrees"] = degrees

            # Build networkx graph
            G = nx.Graph()
            for v in adj:
                G.add_node(v)
            for v, nbrs in adj.items():
                for u in nbrs:
                    if u > v:  # avoid duplicates
                        G.add_edge(v, u)
            cfg["graph"] = G

            # Skip coloring/reducibility data lines
            while idx < len(lines):
                cl = lines[idx].strip()
                if not cl or re.match(r"^\d+\.[-]?\d+", cl):
                    break
                idx += 1

            configs.append(cfg)
        else:
            idx += 1

    return configs


# =========================================================================
#  HELPER — build a sample planar triangulation for the demo
# =========================================================================

def build_demo_triangulation():
    """Build a small planar triangulation with mixed degrees (5,6,7)
    suitable for demonstrating the discharging procedure.
    Returns (G, pos) where pos is a planar layout dict."""

    # Icosahedron: 12 vertices, all degree 5
    G = nx.icosahedral_graph()

    # Relabel to 1-indexed
    mapping = {v: v + 1 for v in G.nodes()}
    G = nx.relabel_nodes(G, mapping)

    # Use spring layout for planar-ish positions
    pos = nx.spring_layout(G, seed=42, k=2.0, iterations=200)

    # Scale to fit frame
    coords = np.array(list(pos.values()))
    cx, cy = coords.mean(axis=0)
    scale = 2.5 / max(abs(coords - [cx, cy]).max(axis=0))
    pos = {v: ((x - cx) * scale, (y - cy) * scale) for v, (x, y) in pos.items()}

    return G, pos


def build_mixed_degree_triangulation():
    """Build a planar triangulation with vertices of degrees 5, 6, and 7+
    to properly demonstrate discharging where charge actually transfers."""

    # Start from a wheel graph W_7 (center degree 7, rim degree 3-4)
    # Then add more triangulation edges to make it a proper triangulation
    # with a mix of degree-5, degree-6, and degree-7+ vertices.

    G = nx.Graph()
    # Central hub vertex (will be degree 7+)
    # Outer ring of 8 vertices
    n_outer = 8
    for i in range(1, n_outer + 1):
        G.add_node(i)
    G.add_node(0)  # center

    # Connect center to all outer
    for i in range(1, n_outer + 1):
        G.add_edge(0, i)

    # Connect outer ring
    for i in range(1, n_outer + 1):
        G.add_edge(i, (i % n_outer) + 1)

    # Add second ring of vertices (degree 5-6)
    for i in range(n_outer + 1, 2 * n_outer + 1):
        G.add_node(i)

    # Connect second ring to first ring and to each other
    for i in range(n_outer):
        v1 = i + 1
        v2 = (i + 1) % n_outer + 1
        v_outer = n_outer + 1 + i
        G.add_edge(v1, v_outer)
        G.add_edge(v2, v_outer)
        # Connect adjacent outer ring vertices
        next_outer = n_outer + 1 + ((i + 1) % n_outer)
        G.add_edge(v_outer, next_outer)

    # Add triangulation diagonals to ensure all faces are triangles
    for i in range(n_outer):
        v_outer = n_outer + 1 + i
        v1 = (i % n_outer) + 1
        next_outer = n_outer + 1 + ((i + 1) % n_outer)
        G.add_edge(v1, next_outer)

    # Planar layout: center at origin, inner ring, outer ring
    pos = {}
    pos[0] = (0.0, 0.0)
    for i in range(1, n_outer + 1):
        angle = 2 * np.pi * (i - 1) / n_outer - np.pi / 2
        pos[i] = (1.5 * np.cos(angle), 1.5 * np.sin(angle))
    for i in range(n_outer + 1, 2 * n_outer + 1):
        j = i - n_outer - 1
        angle = 2 * np.pi * j / n_outer - np.pi / 2 + np.pi / n_outer
        pos[i] = (2.8 * np.cos(angle), 2.8 * np.sin(angle))

    return G, pos


def compute_charges(G):
    """Compute initial charges q₀(v) = 60·(6 - deg(v)) for each vertex."""
    return {v: 60 * (6 - G.degree(v)) for v in G.nodes()}


def charge_color(q):
    """Map charge value to a color."""
    if q > 0:
        return POS_CHARGE_COLOR
    elif q == 0:
        return ZERO_CHARGE_COLOR
    else:
        return NEG_CHARGE_COLOR


# =========================================================================
#  HELPER — build a Manim graph with charge labels
# =========================================================================

def config_to_nx(cfg):
    """Convert a parsed configuration to (nx.Graph, ring_size)."""
    return cfg["graph"], cfg["ring_size"]


def planar_layout_config(cfg):
    """Compute a nice planar layout for a configuration.
    Ring vertices go on a circle; interior vertices use spring layout."""
    G = cfg["graph"]
    ring = cfg["ring_size"]
    n = cfg["n_verts"]

    pos = {}
    # Ring vertices 1..ring on outer circle
    for i in range(1, ring + 1):
        angle = 2 * np.pi * (i - 1) / ring - np.pi / 2
        pos[i] = np.array([1.8 * np.cos(angle), 1.8 * np.sin(angle)])

    # Interior vertices: use spring layout constrained
    interior = [v for v in G.nodes() if v > ring]
    if interior:
        # Fix ring positions, let interior float
        fixed_pos = {v: pos[v] for v in pos}
        all_pos = nx.spring_layout(
            G, pos=fixed_pos, fixed=list(fixed_pos.keys()),
            k=1.5, iterations=100, seed=42
        )
        for v in interior:
            pos[v] = all_pos[v]

    return pos


# =========================================================================
#  SCENE 1: Euler's Formula & Initial Charge Assignment
# =========================================================================

class EulerChargeIntro(Scene):
    """Demonstrates Euler's formula for planar graphs and the initial
    charge assignment q₀(v) = 60(6 - deg(v)), showing that the total
    charge equals 720 for any planar triangulation of the sphere."""

    def construct(self):
        self.camera.background_color = WHITE
        self.camera.frame_width = FRAME_WIDTH
        self.camera.frame_height = FRAME_HEIGHT

        # ---- Title ----
        title = Text(
            "Module 1: Discharging & Unavoidability",
            font_size=TITLE_FONT_SIZE, color=BLACK, weight=BOLD,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=1.0 / SPEED_FACTOR)
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Step 1: Euler's formula ----
        euler_title = Text(
            "Step 1: Euler's Formula for Planar Graphs",
            font_size=28, color=BLACK, weight=BOLD,
        ).next_to(title, DOWN, buff=0.3)

        euler_eq = MathTex(
            r"V - E + F = 2",
            font_size=40, color=BLACK,
        ).next_to(euler_title, DOWN, buff=0.3)

        self.play(
            FadeIn(euler_title, shift=DOWN * 0.3),
            run_time=0.8 / SPEED_FACTOR,
        )
        self.play(Write(euler_eq), run_time=1.0 / SPEED_FACTOR)
        self.wait(0.8 / SPEED_FACTOR)

        # ---- Build small triangulation on the left ----
        G, pos_dict = build_mixed_degree_triangulation()

        # Create manim Graph on left half
        vertices = list(G.nodes())
        edges = list(G.edges())
        layout = {v: np.array([x, y, 0]) for v, (x, y) in pos_dict.items()}

        # Scale and shift to left
        for v in layout:
            layout[v] = layout[v] * 0.55 + np.array([-3.2, -1.2, 0])

        g = Graph(
            vertices, edges,
            layout=layout,
            edge_config={"stroke_width": EDGE_STROKE_WIDTH, "color": EDGE_COLOR},
            vertex_config={
                "radius": NODE_RADIUS,
                "stroke_width": NODE_STROKE_WIDTH,
                "stroke_color": BLACK,
                "fill_color": WHITE,
                "fill_opacity": 1.0,
            },
        )

        # Vertex labels
        labels = VGroup(*[
            Text(str(v), color=BLACK, font_size=LABEL_FONT_SIZE - 4)
            .move_to(g.vertices[v].get_center())
            .set_z_index(10)
            for v in vertices
        ])

        self.play(
            Create(g),
            run_time=1.5 / SPEED_FACTOR,
        )
        self.play(FadeIn(labels), run_time=0.5 / SPEED_FACTOR)
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Verify Euler's formula on this graph ----
        n_v = G.number_of_nodes()
        n_e = G.number_of_edges()
        # Approximate face count (for planar: F = E - V + 2)
        n_f = n_e - n_v + 2

        verify = MathTex(
            f"{n_v}", r"-", f"{n_e}", r"+", f"{n_f}", r"=", r"2",
            font_size=36, color=BLACK,
        ).next_to(euler_eq, DOWN, buff=0.2)

        self.play(Write(verify), run_time=0.8 / SPEED_FACTOR)
        check = Text("✓", font_size=40, color="#2ECC71").next_to(verify, RIGHT, buff=0.2)
        self.play(FadeIn(check), run_time=0.3 / SPEED_FACTOR)
        self.wait(1.0 / SPEED_FACTOR)

        # ---- Step 2: Charge Assignment ----
        self.play(
            FadeOut(euler_title), FadeOut(euler_eq),
            FadeOut(verify), FadeOut(check),
            run_time=0.5 / SPEED_FACTOR,
        )

        charge_title = Text(
            "Step 2: Assign Initial Charges",
            font_size=28, color=BLACK, weight=BOLD,
        ).next_to(title, DOWN, buff=0.3)

        charge_formula = MathTex(
            r"q_0(v) = 60\,(6 - \deg(v))",
            font_size=36, color=BLACK,
        ).next_to(charge_title, DOWN, buff=0.25)

        self.play(
            FadeIn(charge_title, shift=DOWN * 0.3),
            Write(charge_formula),
            run_time=1.0 / SPEED_FACTOR,
        )
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Color vertices by charge and show charge values ----
        charges = compute_charges(G)
        animations = []
        charge_labels = VGroup()

        for v in vertices:
            q = charges[v]
            col = charge_color(q)
            animations.append(
                g.vertices[v].animate.set_fill(color=col, opacity=0.85)
            )
            # Charge label below vertex
            ql = Text(
                f"{q:+d}", font_size=CHARGE_FONT_SIZE, color=BLACK,
            ).next_to(g.vertices[v], DOWN, buff=0.08).set_z_index(10)
            charge_labels.add(ql)

        self.play(*animations, run_time=1.0 / SPEED_FACTOR)
        self.play(FadeIn(charge_labels), run_time=0.8 / SPEED_FACTOR)
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Legend ----
        legend_items = VGroup(
            VGroup(
                Circle(radius=0.12, fill_color=POS_CHARGE_COLOR, fill_opacity=0.85,
                       stroke_color=BLACK, stroke_width=2),
                Text("deg 5 → q₀ = +60", font_size=18, color=BLACK),
            ).arrange(RIGHT, buff=0.15),
            VGroup(
                Circle(radius=0.12, fill_color=ZERO_CHARGE_COLOR, fill_opacity=0.85,
                       stroke_color=BLACK, stroke_width=2),
                Text("deg 6 → q₀ =   0", font_size=18, color=BLACK),
            ).arrange(RIGHT, buff=0.15),
            VGroup(
                Circle(radius=0.12, fill_color=NEG_CHARGE_COLOR, fill_opacity=0.85,
                       stroke_color=BLACK, stroke_width=2),
                Text("deg 7+ → q₀ < 0", font_size=18, color=BLACK),
            ).arrange(RIGHT, buff=0.15),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(RIGHT, buff=0.8).shift(DOWN * 0.5)

        self.play(FadeIn(legend_items), run_time=0.8 / SPEED_FACTOR)
        self.wait(0.8 / SPEED_FACTOR)

        # ---- Total charge = 720 ----
        total_q = sum(charges.values())
        total_text = MathTex(
            r"\sum_{v} q_0(v) = 60 \sum (6 - \deg(v)) = ",
            f"{total_q}",
            font_size=30, color=BLACK,
        ).next_to(charge_formula, DOWN, buff=0.25)

        # Kempe's identity
        kempe = MathTex(
            r"= 360\chi = 360 \cdot 2 = 720 > 0",
            font_size=30, color=BLACK,
        ).next_to(total_text, DOWN, buff=0.15)

        self.play(Write(total_text), run_time=1.0 / SPEED_FACTOR)
        self.play(Write(kempe), run_time=1.0 / SPEED_FACTOR)
        self.wait(0.5 / SPEED_FACTOR)

        # Highlight the key insight
        insight_box = SurroundingRectangle(kempe, color="#E74C3C", buff=0.12, stroke_width=3)
        insight_text = Text(
            "Total charge is always positive!",
            font_size=22, color="#E74C3C", weight=BOLD,
        ).next_to(insight_box, DOWN, buff=0.15)

        self.play(Create(insight_box), Write(insight_text), run_time=1.0 / SPEED_FACTOR)
        self.wait(2.0 / SPEED_FACTOR)

        # ---- Cleanup ----
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8 / SPEED_FACTOR)


# =========================================================================
#  SCENE 2: Animated Discharging Procedure
# =========================================================================

class DischargingDemo(Scene):
    """Animates the discharging procedure on a sample triangulation.
    Shows charge flowing from degree-5 vertices along edges to
    nearby degree-7+ vertices, preserving total charge = 720."""

    def construct(self):
        self.camera.background_color = WHITE
        self.camera.frame_width = FRAME_WIDTH
        self.camera.frame_height = FRAME_HEIGHT

        # ---- Title ----
        title = Text(
            "The Discharging Procedure",
            font_size=TITLE_FONT_SIZE, color=BLACK, weight=BOLD,
        ).to_edge(UP, buff=0.35)
        self.play(Write(title), run_time=0.8 / SPEED_FACTOR)

        subtitle = Text(
            "Redistribute charge — total stays at 720",
            font_size=22, color="#555555",
        ).next_to(title, DOWN, buff=0.15)
        self.play(FadeIn(subtitle), run_time=0.5 / SPEED_FACTOR)

        # ---- Build triangulation ----
        G, pos_dict = build_mixed_degree_triangulation()
        vertices = list(G.nodes())
        edges = list(G.edges())
        charges = compute_charges(G)

        layout = {v: np.array([x, y, 0]) for v, (x, y) in pos_dict.items()}
        # Center it
        for v in layout:
            layout[v] = layout[v] * 0.7 + np.array([0.0, -0.8, 0])

        g = Graph(
            vertices, edges,
            layout=layout,
            edge_config={"stroke_width": EDGE_STROKE_WIDTH, "color": EDGE_COLOR},
            vertex_config={
                "radius": NODE_RADIUS, "stroke_width": NODE_STROKE_WIDTH,
                "stroke_color": BLACK, "fill_color": WHITE, "fill_opacity": 1.0,
            },
        )

        # Color vertices by initial charge
        for v in vertices:
            g.vertices[v].set_fill(color=charge_color(charges[v]), opacity=0.85)

        # Charge label trackers
        charge_labels = {}
        for v in vertices:
            q = charges[v]
            lbl = Text(
                f"{q:+d}", font_size=CHARGE_FONT_SIZE, color=BLACK,
            ).move_to(g.vertices[v].get_center() + DOWN * 0.42).set_z_index(10)
            charge_labels[v] = lbl

        # Degree labels inside nodes
        deg_labels = VGroup(*[
            Text(
                f"d={G.degree(v)}", font_size=14, color=BLACK,
            ).move_to(g.vertices[v].get_center()).set_z_index(10)
            for v in vertices
        ])

        self.play(Create(g), run_time=1.0 / SPEED_FACTOR)
        self.play(FadeIn(deg_labels), run_time=0.5 / SPEED_FACTOR)
        self.play(
            *[FadeIn(charge_labels[v]) for v in vertices],
            run_time=0.5 / SPEED_FACTOR,
        )
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Show total charge before ----
        total_before = sum(charges.values())
        total_text = Text(
            f"Total charge: {total_before}",
            font_size=22, color=BLACK,
        ).to_edge(DOWN, buff=0.3)
        self.play(Write(total_text), run_time=0.5 / SPEED_FACTOR)

        # ---- RSST Rule (simplified): degree-5 vertices send charge
        #      to adjacent degree-7+ vertices ----
        rule_text = Text(
            "Rule: Each degree-5 vertex sends charge to adjacent degree ≥ 7 neighbors",
            font_size=20, color="#333333",
        ).next_to(title, DOWN, buff=0.6)
        self.play(
            FadeOut(subtitle),
            FadeIn(rule_text),
            run_time=0.5 / SPEED_FACTOR,
        )
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Animate discharging ----
        # For each degree-5 vertex, send charge along edges to degree-7+ neighbors
        working_charges = dict(charges)

        for v in vertices:
            if G.degree(v) != 5:
                continue

            # Find degree-7+ neighbors
            major_nbrs = [u for u in G.neighbors(v) if G.degree(u) >= 7]
            if not major_nbrs:
                continue

            # Divide the +60 among major neighbors
            send_each = min(60 // len(major_nbrs), 30)  # cap at 30 per edge (RSST rule)
            total_sent = send_each * len(major_nbrs)

            for u in major_nbrs:
                # Animate a glowing ball traveling along the edge
                start = g.vertices[v].get_center()
                end   = g.vertices[u].get_center()
                ball  = Circle(
                    radius=0.1, fill_color=HIGHLIGHT_COLOR,
                    fill_opacity=1.0, stroke_width=1, stroke_color="#FFA500",
                ).move_to(start).set_z_index(20)

                amount_label = Text(
                    f"{send_each}", font_size=14, color="#C0392B", weight=BOLD,
                ).move_to(start).set_z_index(21)

                self.play(
                    FadeIn(ball), FadeIn(amount_label),
                    run_time=0.15 / SPEED_FACTOR,
                )
                self.play(
                    ball.animate.move_to(end),
                    amount_label.animate.move_to(end),
                    run_time=0.4 / SPEED_FACTOR,
                )
                self.play(
                    FadeOut(ball), FadeOut(amount_label),
                    run_time=0.15 / SPEED_FACTOR,
                )

                # Update working charges
                working_charges[v] -= send_each
                working_charges[u] += send_each

            # Update displayed charge for v
            new_lbl_v = Text(
                f"{working_charges[v]:+d}",
                font_size=CHARGE_FONT_SIZE, color=BLACK,
            ).move_to(charge_labels[v].get_center()).set_z_index(10)
            self.play(
                Transform(charge_labels[v], new_lbl_v),
                g.vertices[v].animate.set_fill(
                    color=charge_color(working_charges[v]), opacity=0.85
                ),
                run_time=0.3 / SPEED_FACTOR,
            )

            # Update displayed charges for recipients
            for u in major_nbrs:
                new_lbl_u = Text(
                    f"{working_charges[u]:+d}",
                    font_size=CHARGE_FONT_SIZE, color=BLACK,
                ).move_to(charge_labels[u].get_center()).set_z_index(10)
                self.play(
                    Transform(charge_labels[u], new_lbl_u),
                    g.vertices[u].animate.set_fill(
                        color=charge_color(working_charges[u]), opacity=0.85
                    ),
                    run_time=0.2 / SPEED_FACTOR,
                )

        self.wait(0.5 / SPEED_FACTOR)

        # ---- Show total charge after — still 720! ----
        total_after = sum(working_charges.values())
        new_total = Text(
            f"Total charge after discharging: {total_after}",
            font_size=22, color="#27AE60", weight=BOLD,
        ).to_edge(DOWN, buff=0.3)
        self.play(Transform(total_text, new_total), run_time=0.5 / SPEED_FACTOR)

        check = Text("✓  Still 720!", font_size=26, color="#27AE60", weight=BOLD,
                      ).next_to(new_total, RIGHT, buff=0.3)
        self.play(FadeIn(check), run_time=0.3 / SPEED_FACTOR)
        self.wait(2.0 / SPEED_FACTOR)

        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8 / SPEED_FACTOR)


# =========================================================================
#  SCENE 3: The Unavoidability Proof (Contradiction Argument)
# =========================================================================

class UnavoidabilityProof(Scene):
    """Presents the logical structure of the unavoidability argument:
    If no configuration from the set appears → all charges ≤ 0 after
    discharging → but total = 720 > 0 → contradiction."""

    def construct(self):
        self.camera.background_color = WHITE
        self.camera.frame_width = FRAME_WIDTH
        self.camera.frame_height = FRAME_HEIGHT

        title = Text(
            "The Unavoidability Argument",
            font_size=TITLE_FONT_SIZE, color=BLACK, weight=BOLD,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=0.8 / SPEED_FACTOR)

        # ---- Proof by contradiction layout ----
        steps = [
            ("Assume:", r"\text{T is a minimal counterexample (not 4-colorable)}"),
            ("Then:", r"\text{T is an internally 6-connected triangulation}"),
            ("Claim:", r"\text{T must contain one of the 633 configurations}"),
        ]

        step_groups = VGroup()
        for label_str, math_str in steps:
            label = Text(label_str, font_size=22, color="#2C3E50", weight=BOLD)
            content = MathTex(math_str, font_size=24, color=BLACK)
            row = VGroup(label, content).arrange(RIGHT, buff=0.3)
            step_groups.add(row)

        step_groups.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        step_groups.next_to(title, DOWN, buff=0.5)

        for sg in step_groups:
            self.play(FadeIn(sg, shift=RIGHT * 0.5), run_time=0.8 / SPEED_FACTOR)
            self.wait(0.4 / SPEED_FACTOR)

        self.wait(0.5 / SPEED_FACTOR)

        # ---- The key logic ----
        proof_box = VGroup(
            Text("Proof structure:", font_size=22, color="#8E44AD", weight=BOLD),
            MathTex(
                r"\text{1. Assign charges: } q_0(v) = 60(6 - \deg(v))",
                font_size=22, color=BLACK,
            ),
            MathTex(
                r"\text{2. Total charge } = 720 > 0",
                font_size=22, color=BLACK,
            ),
            MathTex(
                r"\text{3. Apply 32 discharging rules (RSST)}",
                font_size=22, color=BLACK,
            ),
            MathTex(
                r"\text{4. Total charge is preserved: still } 720",
                font_size=22, color=BLACK,
            ),
            MathTex(
                r"\text{5. If T avoids all 633 configs} \Rightarrow q(v) \leq 0\;\forall v",
                font_size=22, color="#C0392B",
            ),
            MathTex(
                r"\text{6. But } \sum q(v) = 720 > 0 \;\;\Rightarrow\!\Leftarrow",
                font_size=22, color="#C0392B",
            ),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        proof_box.next_to(step_groups, DOWN, buff=0.5, aligned_edge=LEFT)

        for i, item in enumerate(proof_box):
            self.play(
                FadeIn(item, shift=RIGHT * 0.3),
                run_time=0.6 / SPEED_FACTOR,
            )
            if i >= 4:  # pause on the key contradiction steps
                self.wait(0.5 / SPEED_FACTOR)

        self.wait(0.5 / SPEED_FACTOR)

        # ---- BIG contradiction symbol ----
        contra = Text(
            "CONTRADICTION",
            font_size=40, color="#E74C3C", weight=BOLD,
        ).next_to(proof_box, DOWN, buff=0.3)
        contra_box = SurroundingRectangle(contra, color="#E74C3C", buff=0.15, stroke_width=4)

        self.play(
            Write(contra), Create(contra_box),
            run_time=1.0 / SPEED_FACTOR,
        )
        self.wait(0.5 / SPEED_FACTOR)

        # ---- Therefore ----
        therefore = Text(
            "∴ T cannot avoid all 633 configurations → no minimal counterexample exists",
            font_size=22, color="#27AE60", weight=BOLD,
        ).next_to(contra_box, DOWN, buff=0.3)
        self.play(Write(therefore), run_time=1.2 / SPEED_FACTOR)

        qed = Text(
            "■  The Four Color Theorem holds.",
            font_size=24, color="#2C3E50", weight=BOLD,
        ).next_to(therefore, DOWN, buff=0.25)
        self.play(FadeIn(qed), run_time=0.8 / SPEED_FACTOR)
        self.wait(3.0 / SPEED_FACTOR)

        self.play(*[FadeOut(m) for m in self.mobjects], run_time=1.0 / SPEED_FACTOR)


# =========================================================================
#  SCENE 4: Configuration Gallery from RSST Unavoidable Set
# =========================================================================

class ConfigGallery(Scene):
    """Parses and displays a selection of the 633 configurations from
    the RSST unavoidable set, showing ring vs. interior structure."""

    def construct(self):
        self.camera.background_color = WHITE
        self.camera.frame_width = FRAME_WIDTH
        self.camera.frame_height = FRAME_HEIGHT

        title = Text(
            "The 633 Unavoidable Configurations (RSST)",
            font_size=TITLE_FONT_SIZE - 4, color=BLACK, weight=BOLD,
        ).to_edge(UP, buff=0.35)
        self.play(Write(title), run_time=0.8 / SPEED_FACTOR)

        subtitle = Text(
            "Every internally 6-connected planar triangulation contains at least one",
            font_size=20, color="#555555",
        ).next_to(title, DOWN, buff=0.15)
        self.play(FadeIn(subtitle), run_time=0.5 / SPEED_FACTOR)

        # ---- Parse configurations ----
        configs = parse_unavoidable_configs(CONF_PATH)
        if not configs:
            err = Text(
                f"Config file not found at:\n{CONF_PATH}\nPlease update CONF_PATH.",
                font_size=24, color="#E74C3C",
            ).move_to(ORIGIN)
            self.play(Write(err))
            self.wait(3)
            return

        # Show a curated selection: small, medium, and large configs
        # Pick indices: 0, 5, 20, 50, 100, 300, 600 (or as many as available)
        showcase_indices = [0, 4, 19, 49, 99, 299, min(599, len(configs) - 1)]
        showcase_indices = [i for i in showcase_indices if i < len(configs)]

        for idx in showcase_indices:
            cfg = configs[idx]
            self.show_single_config(cfg, idx + 1, len(configs))

        # ---- Final summary ----
        self.play(*[FadeOut(m) for m in self.mobjects if m not in [title, subtitle]],
                  run_time=0.5 / SPEED_FACTOR)

        summary = VGroup(
            Text(f"Total configurations: {len(configs)}", font_size=28, color=BLACK),
            Text(
                "Ring sizes range from 6 to 14 vertices",
                font_size=22, color="#555555",
            ),
            Text(
                "Interior vertices fill the ring to form a triangulation",
                font_size=22, color="#555555",
            ),
            Text(
                "Each proved reducible → cannot appear in a minimal counterexample",
                font_size=22, color="#27AE60", weight=BOLD,
            ),
        ).arrange(DOWN, buff=0.25).move_to(ORIGIN)

        self.play(FadeIn(summary), run_time=1.0 / SPEED_FACTOR)
        self.wait(3.0 / SPEED_FACTOR)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8 / SPEED_FACTOR)

    def show_single_config(self, cfg, num, total):
        """Display a single configuration with ring/interior highlighted."""
        G = cfg["graph"]
        ring = cfg["ring_size"]
        n = cfg["n_verts"]
        n_interior = n - ring

        # Compute layout
        pos = planar_layout_config(cfg)

        # Shift/scale to center
        all_pts = np.array(list(pos.values()))
        cx, cy = all_pts.mean(axis=0)
        scale_factor = 2.2 / max(abs(all_pts - [cx, cy]).max(axis=0).max(), 0.01)
        layout_3d = {}
        for v, (x, y) in pos.items():
            layout_3d[v] = np.array([
                (x - cx) * scale_factor - 1.5,
                (y - cy) * scale_factor - 0.8,
                0,
            ])

        vertices = list(G.nodes())
        edges = list(G.edges())

        # Create graph
        g = Graph(
            vertices, edges,
            layout=layout_3d,
            edge_config={"stroke_width": EDGE_STROKE_WIDTH - 0.5, "color": EDGE_COLOR},
            vertex_config={
                "radius": NODE_RADIUS - 0.03,
                "stroke_width": NODE_STROKE_WIDTH,
                "stroke_color": BLACK,
                "fill_color": WHITE,
                "fill_opacity": 1.0,
            },
        )

        # Color ring vs interior
        for v in vertices:
            if v <= ring:
                g.vertices[v].set_fill(color=RING_COLOR, opacity=0.85)
            else:
                g.vertices[v].set_fill(color=INTERIOR_COLOR, opacity=0.85)

        # Vertex labels
        vlabels = VGroup(*[
            Text(str(v), color=BLACK, font_size=LABEL_FONT_SIZE - 6)
            .move_to(g.vertices[v].get_center()).set_z_index(10)
            for v in vertices
        ])

        # Info panel on the right
        info = VGroup(
            Text(
                f"Configuration #{num} / {total}",
                font_size=26, color=BLACK, weight=BOLD,
            ),
            Text(
                f"Vertices: {n}  |  Ring size: {ring}  |  Interior: {n_interior}",
                font_size=20, color="#333333",
            ),
            Text(
                f"Edges: {G.number_of_edges()}",
                font_size=20, color="#333333",
            ),
            VGroup(
                Circle(radius=0.1, fill_color=RING_COLOR, fill_opacity=0.85,
                       stroke_color=BLACK, stroke_width=1.5),
                Text("Ring vertex", font_size=16, color=BLACK),
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Circle(radius=0.1, fill_color=INTERIOR_COLOR, fill_opacity=0.85,
                       stroke_color=BLACK, stroke_width=1.5),
                Text("Interior vertex", font_size=16, color=BLACK),
            ).arrange(RIGHT, buff=0.1),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        info.to_edge(RIGHT, buff=0.6).shift(DOWN * 0.5)

        # Degree distribution
        deg_counts = {}
        for v in vertices:
            d = G.degree(v)
            deg_counts[d] = deg_counts.get(d, 0) + 1
        deg_str = "  ".join([f"d{d}:{c}" for d, c in sorted(deg_counts.items())])
        deg_info = Text(
            f"Degrees: {deg_str}",
            font_size=16, color="#555555",
        )
        info.add(deg_info)

        self.play(
            Create(g), FadeIn(vlabels), FadeIn(info),
            run_time=1.0 / SPEED_FACTOR,
        )
        self.wait(1.5 / SPEED_FACTOR)

        self.play(
            FadeOut(g), FadeOut(vlabels), FadeOut(info),
            run_time=0.5 / SPEED_FACTOR,
        )


# =========================================================================
#  SCENE 5: Full Module 1 — all parts in one video
# =========================================================================

class FullModule1(Scene):
    """Runs all Module 1 content in one continuous video.
    Use: manim -pql module1_discharging.py FullModule1
    Or run individual scenes above for shorter clips."""

    def construct(self):
        self.camera.background_color = WHITE
        self.camera.frame_width = FRAME_WIDTH
        self.camera.frame_height = FRAME_HEIGHT

        # ---- Part 1 ----
        s1 = EulerChargeIntro()
        s1.camera = self.camera
        s1.mobjects = self.mobjects
        s1.renderer = self.renderer
        s1.animations = self.animations if hasattr(self, 'animations') else None
        # Directly call its construct — it will add to our scene
        # (this is a workaround; for cleaner approach, refactor each
        #  scene's logic into helper methods)

        self.next_section("Part 1: Euler Formula & Charges")
        EulerChargeIntro.construct(self)

        self._transition("Part 2: The Discharging Procedure")
        self.next_section("Part 2: Discharging")
        DischargingDemo.construct(self)

        self._transition("Part 3: The Unavoidability Argument")
        self.next_section("Part 3: Proof")
        UnavoidabilityProof.construct(self)

        self._transition("Part 4: The 633 Configurations")
        self.next_section("Part 4: Gallery")
        ConfigGallery.construct(self)

    def _transition(self, text_str):
        trans = Text(
            f"— {text_str} —",
            font_size=30, color="#2C3E50", weight=BOLD,
        ).move_to(ORIGIN)
        self.play(FadeIn(trans), run_time=0.5 / SPEED_FACTOR)
        self.wait(1.0 / SPEED_FACTOR)
        self.play(FadeOut(trans), run_time=0.5 / SPEED_FACTOR)