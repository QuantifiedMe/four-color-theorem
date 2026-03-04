#!/usr/bin/env python3
# ============================================================================
# kempe_proof.py  —  Kempe's Proof: Easy Cases & Degree-5 Chain Success
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
# This module animates Alfred Kempe's 1879 "proof" of the Four-Color Theorem.
# It demonstrates the inductive argument for vertices of degree 3, 4, and 5,
# including the Kempe chain technique that underpins every subsequent proof.
#
# Scenes:
#
#   KempeEasyCases
#       The inductive argument for vertices of degree 3 and 4.  A target
#       vertex is removed from a small triangulation, the reduced graph
#       is colored by "induction," and the vertex is reinserted.  Because
#       only 3 (or 4, with a pair sharing a color) neighbors exist, a free
#       color is always available.
#
#   KempeChainSuccess
#       The degree-5 case where Kempe's chain argument works.  A vertex v
#       of degree 5 has all four colors on its ring.  The Kempe chain
#       K(Purple, Pink) from v2 does NOT reach v5; swapping frees Purple
#       for v0.
#
#   KempeProofComplete
#       Both scenes rendered as a single continuous video.
#
# ============================================================================
# USAGE
# ============================================================================
#
#   manim -qh kempe_proof.py KempeEasyCases
#   manim -qh kempe_proof.py KempeChainSuccess
#   manim -qh kempe_proof.py KempeProofComplete
#
# ============================================================================
# REFERENCES
# ============================================================================
#
#   [1] A. B. Kempe, "On the Geographical Problem of the Four Colours,"
#       Amer. J. Math., vol. 2, no. 3, pp. 193-200, 1879.
#
# ============================================================================

from manim import *
import numpy as np
import sys

from kempe_common import (
    # Constants
    SPEED, CONTENT_CENTER_Y, NODE_STROKE_WIDTH,
    KEMPE_CHAIN_WIDTH, KEMPE_GLOW_WIDTH,
    C_BLUE, C_PURPLE, C_YELLOW, C_PINK,
    NARR_COLOR, NARR_SUCCESS_COLOR, NARR_EMPHASIS_COLOR,
    # Graph builders
    build_degree3_graph, build_degree4_graph, build_degree5_success_graph,
    # Utilities
    make_manim_graph, color_vertex, flash_vertex,
    find_kempe_chain, swap_kempe_chain, kempe_chain_edges,
    build_header, show_narration, add_persistent_narration,
    copy_to_output,
)


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

    No narration overlay — the animation speaks for itself.
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
        for v, c in sorted(init_coloring.items()):
            color_vertex(self, g, v, c, run_time=0.15)
        self.wait(1.0 * SPEED)

        # Highlight the shared-color pair
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

        # Compute and display the Kempe chain
        coloring = dict(init_coloring)
        chain = find_kempe_chain(G, coloring, 2, C_PURPLE, C_PINK)
        chain_edges = kempe_chain_edges(G, chain)

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
        self.wait(1.5 * SPEED)

        # Perform the swap
        swaps = swap_kempe_chain(coloring, chain, C_PURPLE, C_PINK)
        for v_sw, old_c, new_c in swaps:
            color_vertex(self, g, v_sw, new_c, run_time=0.3)
        self.play(FadeOut(glow_lines), run_time=0.5)
        for v in chain:
            g.vertices[v].set_stroke(BLACK, width=NODE_STROKE_WIDTH)
        self.wait(0.8 * SPEED)

        # Assign the freed color to v0
        color_vertex(self, g, 0, C_PURPLE, run_time=0.6)
        flash_vertex(self, g, 0, color=GREEN)
        self.wait(2.0 * SPEED)


# ============================================================================
# COMBINED SCENE: KempeProofComplete
# ============================================================================

class KempeProofComplete(Scene):
    """Both Kempe proof scenes rendered as a single continuous video.

    Plays KempeEasyCases → KempeChainSuccess with a brief transition.
    """

    def construct(self):
        self.camera.background_color = WHITE

        # Act I: Easy Cases (degree 3 and 4)
        KempeEasyCases.construct(self)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
        self.wait(0.5)

        # Act II: Chain Success (degree 5, chain isolated)
        KempeChainSuccess.construct(self)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    scenes = {
        "KempeEasyCases":     KempeEasyCases,
        "KempeChainSuccess":  KempeChainSuccess,
        "KempeProofComplete": KempeProofComplete,
    }

    if len(sys.argv) < 2:
        print("Kempe's Proof — Easy Cases & Degree-5 Success")
        print("=" * 50)
        print("\nAvailable scenes:")
        for name in scenes:
            print(f"  manim -qh kempe_proof.py {name}")
        sys.exit(0)