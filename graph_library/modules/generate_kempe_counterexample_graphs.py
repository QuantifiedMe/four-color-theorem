#!/usr/bin/env python3
"""
generate_kempe_counterexample_graphs.py
========================================
Daughter module: generates NetworkX graph objects representing historical
counterexamples to Kempe's 1879 proof of the Four Color Theorem.

Each graph is a maximal planar graph (triangulation) where Kempe's chain
argument fails. Multiple layout embeddings are generated for graphs where
visual variety is valuable (Fritsch, Errera).

Module-specific metadata stored in G.graph:
    year           : int    — year of publication
    author         : str    — originating author(s)
    description    : str    — brief historical note
    embedding_id   : int    — which layout variant (1-indexed)
    graph_family   : str    — family name (e.g. 'fritsch', 'soifer', 'errera')
    is_counterexample : bool — always True for this module

References:
    - Fritsch & Fritsch, "The Four-Color Theorem" (Springer, 1998)
    - Soifer, "The Mathematical Coloring Book" (Springer, 2009)
    - Errera, PhD Dissertation (1921)
    - Kittell, "A Group of Operations on a Partially Colored Map" (1935)
    - Heawood, "Map-Colour Theorem" (1890)
"""

import os
import math
import networkx as nx
import numpy as np
from modules.base_module import compute_layouts, verify_graph

# ---- Module Interface ----
MODULE_NAME = "kempe_counterexample"
MODULE_DESCRIPTION = (
    "Historical counterexamples to Kempe's 1879 proof of the Four Color "
    "Theorem — Fritsch, Soifer, Poussin, Errera, Kittell, Heawood graphs."
)


# ============================================================
# Graph Definitions
# ============================================================

def _make_fritsch_graph():
    """Fritsch Graph — 9 vertices, 21 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(9))
    G.add_edges_from([
        (0, 1), (0, 2), (0, 6), (0, 7), (0, 8),
        (1, 2), (1, 3), (1, 7),
        (2, 3), (2, 4), (2, 8),
        (3, 4), (3, 5), (3, 7),
        (4, 5), (4, 6), (4, 8),
        (5, 6), (5, 7),
        (6, 7), (6, 8),
    ])
    G.graph.update(
        name="Fritsch Graph",
        graph_family="fritsch",
        year=1998,
        author="R. Fritsch & G. Fritsch",
        is_counterexample=True,
        description=(
            "Smallest counterexample to Kempe's chain argument. "
            "A 9-vertex maximal planar graph where two Kempe chains "
            "interfere, preventing the recoloring step from succeeding."
        ),
        # Manual vertex nudges applied after layout computation.
        # Values are (dx, dy) in layout-scale units (scale=5.0).
        # Only applied to embedding 1 (the combinatorial planar layout).
        pos_tweaks={7: (0.0, 0.5)},
    )
    return G


def _make_soifer_graph_1():
    """Soifer Graph 1 — 10 vertices, 24 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(10))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 5), (1, 3), (1, 4), (2, 4), (2, 5),
        (3, 4), (4, 5), (3, 5),
        (3, 6), (3, 7), (4, 7), (4, 8), (5, 8), (5, 6),
        (6, 7), (7, 8), (6, 8),
        (6, 9), (7, 9), (8, 9),
    ])
    G.graph.update(
        name="Soifer Graph 1",
        graph_family="soifer",
        year=2009,
        author="A. Soifer",
        is_counterexample=True,
        description=(
            "Counterexample from Soifer's 'The Mathematical Coloring Book'. "
            "A 10-vertex nested triangulation demonstrating Kempe chain failure."
        ),
    )
    return G


def _make_soifer_graph_2():
    """Soifer Graph 2 — 11 vertices, 27 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(11))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 4), (0, 8),
        (1, 4), (1, 5), (1, 6),
        (2, 6), (2, 7), (2, 8),
        (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (3, 8),
        (3, 9), (4, 9), (5, 9), (8, 9),
        (5, 10), (6, 10), (7, 10), (8, 10),
        (9, 10),
    ])
    G.graph.update(
        name="Soifer Graph 2",
        graph_family="soifer",
        year=2009,
        author="A. Soifer",
        is_counterexample=True,
        description=(
            "An 11-vertex planar triangulation from Soifer's analysis "
            "of Kempe chain failures."
        ),
    )
    return G


def _make_soifer_graph_3():
    """Soifer Graph 3 — 12 vertices, 30 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(12))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 4), (0, 8),
        (1, 4), (1, 5), (1, 6),
        (2, 6), (2, 7), (2, 8),
        (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (3, 8),
        (3, 9), (3, 10), (4, 10),
        (5, 10), (5, 11),
        (6, 11), (7, 11),
        (7, 9), (8, 9),
        (9, 10), (10, 11), (9, 11),
    ])
    G.graph.update(
        name="Soifer Graph 3",
        graph_family="soifer",
        year=2009,
        author="A. Soifer",
        is_counterexample=True,
        description=(
            "A 12-vertex planar triangulation demonstrating Kempe chain "
            "interference."
        ),
    )
    return G


def _make_soifer_graph_4():
    """Soifer Graph 4 — icosahedral graph, 12 vertices, 30 edges."""
    G = nx.icosahedral_graph()
    mapping = {n: i for i, n in enumerate(sorted(G.nodes()))}
    G = nx.relabel_nodes(G, mapping)
    G.graph.update(
        name="Soifer Graph 4 (Icosahedron)",
        graph_family="soifer",
        year=2009,
        author="A. Soifer",
        is_counterexample=True,
        description=(
            "The icosahedral graph (12 vertices, 5-regular). "
            "Every vertex has degree 5, making it a natural setting "
            "for demonstrating Kempe chain conflicts."
        ),
    )
    return G


def _make_poussin_graph():
    """De la Vallée-Poussin Graph — 15 vertices, 39 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(15))
    G.add_edges_from([
        (0, 1), (0, 2), (0, 3), (0, 5), (0, 14),
        (1, 2), (1, 5), (1, 6), (1, 7),
        (2, 3), (2, 7), (2, 8),
        (3, 4), (3, 8), (3, 14),
        (4, 8), (4, 9), (4, 13), (4, 14),
        (5, 6), (5, 10), (5, 14),
        (6, 7), (6, 10), (6, 11),
        (7, 8), (7, 11), (7, 12),
        (8, 9), (8, 12),
        (9, 12), (9, 13),
        (10, 11), (10, 14),
        (11, 12), (11, 13), (11, 14),
        (12, 13),
        (13, 14),
    ])
    G.graph.update(
        name="Poussin Graph",
        graph_family="poussin",
        year=1896,
        author="Ch. de la Vallée-Poussin",
        is_counterexample=True,
        description=(
            "A 15-vertex maximal planar graph constructed by de la "
            "Vallée-Poussin as a counterexample to Kempe's chain argument."
        ),
    )
    return G


def _make_errera_graph():
    """Errera Graph — 17 vertices, 45 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(17))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 4), (0, 8),
        (1, 4), (1, 5), (1, 6),
        (2, 6), (2, 7), (2, 8),
        (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (3, 8),
        (3, 9), (3, 10),
        (4, 10), (4, 11),
        (5, 11), (5, 12),
        (6, 12), (6, 13),
        (7, 13), (7, 14),
        (8, 14), (8, 9),
        (9, 10), (10, 11), (11, 12), (12, 13), (13, 14), (9, 14),
        (9, 15), (10, 15), (11, 15), (14, 15),
        (11, 16), (12, 16), (13, 16), (14, 16),
        (15, 16),
    ])
    G.graph.update(
        name="Errera Graph",
        graph_family="errera",
        year=1921,
        author="A. Errera",
        is_counterexample=True,
        description=(
            "A 17-vertex maximal planar graph from Errera's 1921 "
            "dissertation. Classic counterexample showing that "
            "interchanging colors along one Kempe chain can disrupt another."
        ),
    )
    return G


def _make_kittell_graph():
    """Kittell Graph — 23 vertices, 63 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(23))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 4), (0, 8),
        (1, 4), (1, 5), (1, 6),
        (2, 6), (2, 7), (2, 8),
        (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (3, 8),
        (3, 9), (3, 10),
        (4, 10), (4, 11),
        (5, 11), (5, 12),
        (6, 12), (6, 13),
        (7, 13), (7, 14),
        (8, 14), (8, 9),
        (9, 10), (10, 11), (11, 12), (12, 13), (13, 14), (9, 14),
        (9, 15), (9, 20),
        (10, 15), (10, 16),
        (11, 16), (11, 17),
        (12, 17), (12, 18),
        (13, 18), (13, 19),
        (14, 19), (14, 20),
        (15, 16), (16, 17), (17, 18), (18, 19), (19, 20), (15, 20),
        (15, 21), (16, 21), (17, 21), (20, 21),
        (17, 22), (18, 22), (19, 22), (20, 22),
        (21, 22),
    ])
    G.graph.update(
        name="Kittell Graph",
        graph_family="kittell",
        year=1935,
        author="I. Kittell",
        is_counterexample=True,
        description=(
            "A 23-vertex maximal planar graph from Kittell (1935). "
            "Demonstrates Kempe chain failure in a larger triangulation "
            "with three concentric hexagonal rings."
        ),
    )
    return G


def _make_heawood_counterexample_graph():
    """Heawood Four-Color Counterexample — 25 vertices, 69 edges."""
    G = nx.Graph()
    G.add_nodes_from(range(25))
    G.add_edges_from([
        (0, 1), (0, 2), (1, 2),
        (0, 3), (0, 4), (0, 8),
        (1, 4), (1, 5), (1, 6),
        (2, 6), (2, 7), (2, 8),
        (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (3, 8),
        (3, 9), (3, 10),
        (4, 10), (4, 11),
        (5, 11), (5, 12),
        (6, 12), (6, 13),
        (7, 13), (7, 14),
        (8, 14), (8, 9),
        (9, 10), (10, 11), (11, 12), (12, 13), (13, 14), (9, 14),
        (9, 15), (9, 20),
        (10, 15), (10, 16),
        (11, 16), (11, 17),
        (12, 17), (12, 18),
        (13, 18), (13, 19),
        (14, 19), (14, 20),
        (15, 16), (16, 17), (17, 18), (18, 19), (19, 20), (15, 20),
        (15, 21), (16, 21), (16, 22),
        (17, 22), (17, 23),
        (18, 23), (19, 23),
        (19, 24), (20, 24), (20, 21),
        (21, 22), (22, 23), (23, 24), (24, 21),
        (21, 23),
    ])
    G.graph.update(
        name="Heawood Four-Color Graph",
        graph_family="heawood",
        year=1890,
        author="P. J. Heawood",
        is_counterexample=True,
        description=(
            "The graph Heawood used in 1890 to expose the flaw in Kempe's "
            "1879 proof. This 25-vertex triangulation shows that two Kempe "
            "chain interchanges can conflict, invalidating Kempe's argument."
        ),
    )
    return G


# ============================================================
# Graph Registry — extend this list when adding new graphs
# ============================================================

GRAPH_REGISTRY = [
    # (maker_func, family_name, n_embeddings, expected_V, expected_E)
    (_make_fritsch_graph,               "fritsch",  4,  9,  21),
    (_make_soifer_graph_1,              "soifer",   1, 10,  24),
    (_make_soifer_graph_2,              "soifer",   1, 11,  27),
    (_make_soifer_graph_3,              "soifer",   1, 12,  30),
    (_make_soifer_graph_4,              "soifer",   1, 12,  30),
    (_make_poussin_graph,               "poussin",  1, 15,  39),
    (_make_errera_graph,                "errera",   8, 17,  45),
    (_make_kittell_graph,               "kittell",  1, 23,  63),
    (_make_heawood_counterexample_graph,"heawood",  1, 25,  69),
]


def generate(input_dir=None, output_dir=None, **kwargs):
    """
    Generate all Kempe counterexample graphs.

    Parameters
    ----------
    input_dir : str, optional
        Not used (graphs are hardcoded), kept for interface consistency.
    output_dir : str, optional
        Not used directly by this module.

    Returns
    -------
    dict[str, nx.Graph]
    """
    all_graphs = {}
    family_counters = {}

    for maker, family, n_embed, exp_v, exp_e in GRAPH_REGISTRY:
        G_base = maker()

        # Track per-family index for naming
        family_counters[family] = family_counters.get(family, 0)

        # Verify
        ok = verify_graph(G_base, label=G_base.graph['name'],
                          expected_v=exp_v, expected_e=exp_e)
        if not ok:
            print(f"  WARNING: {G_base.graph['name']} failed verification!")

        # Generate embeddings
        layouts = compute_layouts(G_base, n_embed, seed=100 + len(all_graphs))

        for emb_idx, pos in enumerate(layouts, 1):
            family_counters[family] += 1
            Gi = G_base.copy()

            # Apply any manual vertex nudges (only to embedding 1,
            # i.e. the combinatorial planar layout, unless you want
            # them on every embedding).
            tweaks = G_base.graph.get('pos_tweaks', {})
            if tweaks and emb_idx == 1:
                for v, (dx, dy) in tweaks.items():
                    if v in pos:
                        ox, oy = pos[v]
                        pos[v] = (ox + dx, oy + dy)

            key = f"kempe_{family}_{family_counters[family]}"
            Gi.graph['short_name'] = key
            Gi.graph['pos'] = pos
            Gi.graph['embedding_id'] = emb_idx
            Gi.graph['vertices'] = Gi.number_of_nodes()
            Gi.graph['edges'] = Gi.number_of_edges()
            Gi.graph['source'] = 'kempe_counterexample'

            all_graphs[key] = Gi
            print(f"    → {key}")

    print(f"  Generated {len(all_graphs)} Kempe counterexample graphs.")
    return all_graphs


# ============================================================
# Standalone execution
# ============================================================
if __name__ == "__main__":
    import pickle
    from datetime import datetime

    default_output = os.path.join(
        os.path.dirname(__file__), '..', 'output', 'kempe_counterexample'
    )

    print("=" * 75)
    print("Kempe Counterexample Graphs — Standalone Mode")
    print("=" * 75)

    graphs = generate()

    if graphs:
        os.makedirs(default_output, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(
            default_output, f"kempe_counterexample_graphs_{ts}.pkl"
        )
        with open(out_path, 'wb') as f:
            pickle.dump(graphs, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"\nSaved {len(graphs)} graphs → {out_path}")

        # Summary
        print(f"\n{'Key':<35s} {'Name':<35s} {'V':>3s} {'E':>3s} {'Year':>5s}")
        print("-" * 85)
        for key in sorted(graphs.keys()):
            g = graphs[key]
            print(f"{key:<35s} {g.graph['name']:<35s} "
                  f"{g.graph['vertices']:>3d} {g.graph['edges']:>3d} "
                  f"{g.graph.get('year', ''):>5}")
