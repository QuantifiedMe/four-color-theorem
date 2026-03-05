# **3D Polyhedra Module — Research & Architecture Plan**

**Module:** `generate_3D_graphs.py`  
**Project:** Four Color Theorem Graph Library  
**Author:** Tanya Wilcox — MTH-392 Senior Project, Wilkes University, Spring 2026

---

## **1\. Design Philosophy**

Every qualifying graph in the library gets **three distinct 2D layout realizations**, each computed by a different classical algorithm from combinatorial geometry. Each layout is stored as a separate graph entry with a suffix indicating the method:

| Suffix | Algorithm | Character |
| :---- | :---- | :---- |
| `_tutte` | Tutte spring embedding \+ Maxwell-Cremona 3D lift → isometric projection | Convex, symmetric, "rubber-band" aesthetic |
| `_schramm` | Koebe-Andreev-Thurston circle packing on the sphere → stereographic projection | Organic, sphere-respecting, beautiful |
| `_schnyder` | Schnyder wood decomposition → barycentric integer grid | Crisp, grid-aligned, minimal coordinates |

A graph like `kempe_fritsch` thus produces `kempe_fritsch_tutte`, `kempe_fritsch_schramm`, and `kempe_fritsch_schnyder`. With \~1,000 base graphs this yields \~3,000 layout entries. The module compiles once and can take as long as needed — the goal is beautiful, mathematically rigorous images.

Additionally, for graphs sourced from McCooey's Visual Polyhedra database, the **exact analytic 3D coordinates** are preserved as metadata, giving us a fourth coordinate set (the "ground truth" polyhedron) independent of the three algorithmic layouts.

---

## **2\. Mathematical Foundations**

### **2.1 Steinitz's Theorem — The Central Prerequisite**

Steinitz's theorem (1922) states:

A graph G is the edge-skeleton of a 3-dimensional convex polyhedron **if and only if** G is **planar** and **3-vertex-connected**.

This is the gate: only 3-connected planar graphs qualify for polyhedral realization. The module tests every graph with `nx.node_connectivity(G)` and those that fail will need to implement Auxiliary triangulation.  

**Expected results by category:**

| Category | 3-Connected? | Notes |
| :---- | :---- | :---- |
| McCooey polyhedra (\~146) | All YES | Convex polyhedra by definition |
| Kempe counterexamples (\~6) | All YES | Maximal planar triangulations |
| RSST configurations (\~633) | Mixed | Ring boundaries may reduce connectivity |

Graphs that fail the 3-connectivity test are logged and skipped — they have no convex polyhedral realization, so excluding them is mathematically correct.

### **2.2 Approach A — Tutte Embedding \+ Maxwell-Cremona Lifting (`_tutte`)**

**Theory:** Tutte (1963) showed that for any 3-connected planar graph, fixing the outer face as a convex polygon and placing every interior vertex at the barycenter of its neighbors produces a crossing-free drawing with all interior faces convex.

The **Maxwell-Cremona correspondence** (Maxwell 1864, Cremona 1872\) then lifts this 2D drawing to 3D: given an equilibrium stress on the edges (positive interior, negative exterior), a z-coordinate can be computed for each vertex that makes the surface piecewise-linear and convex.

**Algorithm:**

1. Compute planar embedding of G  
2. Choose outer face (largest, or a triangle)  
3. Fix outer face vertices on a convex polygon (regular k-gon)  
4. Solve linear system: each interior vertex \= barycenter of neighbors  
5. Compute equilibrium stress from the Tutte drawing  
6. Lift to 3D via stress-weighted integration  
7. Project to 2D for Manim: `x_2d = x - z*0.5`, `y_2d = y + z*0.3`

**Auxiliary triangulation (for non-triangulated graphs):** The lifting step requires every face to be a triangle. For graphs with non-triangular faces (cubes, Archimedean solids, etc.), we apply temporary **fan triangulation**: pick one vertex per face and add diagonal edges to split each k-gon into k-2 triangles. After lifting, the temporary edges are removed. The 3D coordinates survive because convexity guarantees the original face vertices remain coplanar — the diagonals were redundant constraints.

def auxiliary\_triangulate(G, face\_polygons):

    """Add temporary edges to triangulate all faces.

    Returns: (G\_tri, aux\_edges, original\_faces)"""

    G\_tri \= G.copy()

    aux\_edges \= \[\]

    for face in face\_polygons:

        if len(face) \<= 3:

            continue

        v0 \= face\[0\]

        for i in range(2, len(face) \- 1):

            vi \= face\[i\]

            if not G\_tri.has\_edge(v0, vi):

                G\_tri.add\_edge(v0, vi, auxiliary=True)

                aux\_edges.append((v0, vi))

    return G\_tri, aux\_edges, face\_polygons

**Pros:** Works for all 3-connected planar graphs. Pure linear algebra (scipy sparse solver). Deterministic.

**Cons:** Resulting polyhedra can be "flat" — z-range tiny compared to x,y range. May need post-processing to exaggerate depth.

### **2.3 Approach B — Circle Packing / Koebe-Andreev-Thurston (`_schramm`)**

**Theory:** The circle packing theorem (Koebe 1936, Andreev 1970, Thurston 1985\) guarantees: for every 3-connected planar graph, there exists a packing of circles on the Riemann sphere where adjacent vertices correspond to tangent circles. From this packing, a **midsphere polyhedron** can be constructed where every edge is tangent to the unit sphere.

Schramm's "How to cage an egg" (1992) extended this to show any convex body can be caged by such a polyhedral graph.

**Algorithm:**

1. Compute combinatorial embedding of G  
2. Initialize circle radii (e.g., uniform)  
3. Iteratively adjust radii until tangency conditions converge:  
   - For each vertex, compute the angle sum around it from neighbor radii  
   - Adjust radius to make angle sum \= 2π  
   - Repeat until max adjustment \< tolerance  
4. Place circles on the unit sphere via Möbius transformation  
5. Convert circle centers to polyhedral vertices (tangent plane intersection or stereographic projection)  
6. Project to 2D via stereographic projection for Manim layout

**Pros:** Most beautiful output — respects graph symmetries naturally. Midsphere property is elegant. Well-studied convergence.

**Cons:** Iterative numerical method (typically 50-200 iterations). Coordinates are irrational. Requires careful implementation of inversive distance calculations. Slower than Tutte.

**Implementation note:** We can use Collins & Stephenson's algorithm for circle packing, or adapt the iterative scheme from Mohar (1993). For \~1,000 graphs compiling once, even a slow pure-Python implementation is acceptable.

### **2.4 Approach C — Schnyder Wood Decomposition (`_schnyder`)**

**Theory:** Schnyder (1990) showed that every planar triangulation on n vertices embeds on an (n-2) × (n-2) integer grid with no crossings. The method decomposes internal edges into three directed spanning trees (a **Schnyder wood**), then computes three region-counting coordinates per vertex.

These three coordinates (v₁, v₂, v₃) satisfy v₁ \+ v₂ \+ v₃ \= n-1 and naturally live in barycentric coordinates on a triangle, which provides a 3D surface interpretation.

**Algorithm:**

1. If G is not a triangulation, apply auxiliary triangulation (same technique as Tutte)  
2. Choose outer face (a, b, c) and orient edges inward  
3. Compute Schnyder wood: partition internal edges into three trees T₁, T₂, T₃ rooted at a, b, c respectively  
4. For each interior vertex v, count faces in each of the three "regions" defined by paths to roots → coordinates (v₁, v₂, v₃)  
5. These are integer barycentric coordinates: plot on 2D triangle, or map to 3D plane  
6. For 2D Manim layout: project barycentric coordinates to Cartesian

**Pros:** Integer coordinates — exact, no floating-point issues. Fast (linear time). Grid embedding is clean and visually distinctive. The math is especially elegant for a paper presentation.

**Cons:** Only works for triangulations (but we can always triangulate first and remove auxiliary edges from the rendered layout). The 3D surface is a flat triangular region, not a volumetric polyhedron. Produces a qualitatively different layout than Tutte or Schramm — which is the point.

**Post-processing for non-triangulations:** After computing the Schnyder layout on the triangulated graph, remove auxiliary edges from the graph but keep vertex positions. The resulting layout of the original graph inherits the grid-like quality.

---

## **3\. Data Sources**

### **3.1 McCooey's Visual Polyhedra Database (Tier 1 — \~146 convex polyhedra)**

David McCooey's site at `https://dmccooey.com/polyhedra/` provides **767+ polyhedra** with downloadable `.txt` coordinate files. Each file contains:

Truncated Tetrahedron                         ← Name

C0  \= 1.17518645... \= 3 \* (15 \+ sqrt(5)) / 44   ← Constants (numeric \= symbolic)

C1  \= 1.30901699... \= (3 \+ sqrt(5)) / 4

...

V0   \= ( 0.0,  0.0,  C18)                    ← Vertex 3D coords (using constants)

V1   \= ( 0.0,  0.0, \-C18)

...

{5}  V0  V6  V54  V42  V8                    ← Face definitions ({n} \= n-gon)

{6}  V0  V6  V30  V58  V10  V12

...

**Target set (convex polyhedra only):**

| Category | Count | 4CT Relevance |
| :---- | :---- | :---- |
| Platonic solids | 5 | Core examples, highest symmetry |
| Archimedean solids | 13 | Truncation/rectification demonstrations |
| Catalan solids | 16 | Duals — face-coloring ↔ vertex-coloring duality |
| Johnson solids | 92 | Low-symmetry convex examples |
| Prisms (3- through 12-gon) | 10 | Simple infinite family representatives |
| Antiprisms (3- through 12-gon) | 10 | Triangulated infinite family |
| **Total** | **\~146** | All convex, all 3-connected, all 4-colorable |

**Prior art:** The R package `ropensci/Rpolyhedra` (MIT license) has already scraped all 767 files from McCooey's site. Their scraper (`PolyhedronStateDmccooeyScraper` in `R/polyhedra-lib.R`) uses regex for constants, vertices, and faces — our Python parser follows the same approach.

For McCooey graphs, we store the exact parsed 3D coordinates as `G.graph['mccooey_3d_coordinates']` in addition to the three algorithmic layouts. This gives a ground-truth reference for visual comparison.

### **3.2 Kempe Counterexample Graphs (Tier 2 — \~6 graphs)**

Loaded from `all_planar_graphs.pkl`. These are the historical graphs (Fritsch, Errera, Kittell, Heawood, Poussin, Soifer) that demonstrate failures in Kempe's original 1879 "proof." All are maximal planar triangulations → guaranteed 3-connected → all three layout methods apply directly without auxiliary triangulation.

### **3.3 RSST Unavoidable Configurations (Tier 3 — \~633 qualifying)**

Loaded from `all_planar_graphs.pkl`. The 633 configurations from Robertson-Sanders-Seymour-Thomas (1997). Each is tested for 3-connectivity; those that pass get all three layouts. Those that fail are logged and skipped.

Most RSST configs are triangulations (since the reducibility proof works on triangulations), so the majority should qualify.

### **3.4 Total Graph Count**

| Source | Base Graphs | × 3 Layouts | Entries |
| :---- | :---- | :---- | :---- |
| McCooey polyhedra | \~146 | × 3 | \~438 |
| Kempe counterexamples | \~6 | × 3 | \~18 |
| RSST configs (qualifying) | \~633 | × 3 | \~1,899 |
| **Total** | **\~785** |  | **\~2,355** |

Well under 3,000 entries. Even at 5–10 seconds per graph for circle packing, the full compile is under 3 hours — perfectly acceptable for a one-time build.

---

## **4\. Module Architecture**

### **4.1 File: `modules/generate_3D_graphs.py`**

MODULE\_NAME \= "polyhedra\_3d"

MODULE\_DESCRIPTION \= "Three classical 2D layout algorithms for 3-connected planar graphs"

def generate(input\_dir, output\_dir, \*\*kwargs) \-\> dict\[str, nx.Graph\]:

    """

    For each qualifying graph:

      1\. Compute \_tutte layout  (Tutte \+ Maxwell-Cremona lift → 2D projection)

      2\. Compute \_schramm layout (Circle packing → stereographic projection)

      3\. Compute \_schnyder layout (Schnyder wood → barycentric grid)

    """

### **4.2 Internal Structure**

\# \=== SECTION 1: McCooey Scraper \===

def parse\_mccooey\_txt(text: str) \-\> dict

def scrape\_mccooey\_polyhedra() \-\> dict\[str, nx.Graph\]

\# \=== SECTION 2: Shared Utilities \===

def auxiliary\_triangulate(G, face\_polygons) \-\> (G\_tri, aux\_edges, orig\_faces)

def remove\_auxiliary\_edges(G, aux\_edges) \-\> nx.Graph

def detect\_faces(G, embedding) \-\> list\[list\[node\]\]

def face\_four\_coloring(G, face\_polygons) \-\> dict\[int, int\]

def project\_3d\_to\_2d(pos\_3d, method="isometric") \-\> dict\[node, (x, y)\]

\# \=== SECTION 3: Tutte \+ Maxwell-Cremona \===

def tutte\_embedding(G, outer\_face) \-\> dict\[node, (x, y)\]

def compute\_equilibrium\_stress(G, pos\_2d) \-\> dict\[edge, float\]

def maxwell\_cremona\_lift(G, pos\_2d, stress) \-\> dict\[node, (x, y, z)\]

def layout\_tutte(G, face\_polygons=None) \-\> dict\[node, (x, y)\]

\# \=== SECTION 4: Circle Packing (Schramm) \===

def circle\_packing\_radii(G, embedding, tol=1e-8, max\_iter=500) \-\> dict\[node, float\]

def place\_circles\_on\_sphere(G, radii, embedding) \-\> dict\[node, (x, y, z)\]

def layout\_schramm(G, face\_polygons=None) \-\> dict\[node, (x, y)\]

\# \=== SECTION 5: Schnyder Wood \===

def compute\_schnyder\_wood(G, outer\_face) \-\> (T1, T2, T3)

def schnyder\_coordinates(G, wood, outer\_face) \-\> dict\[node, (v1, v2, v3)\]

def barycentric\_to\_cartesian(bary\_coords) \-\> dict\[node, (x, y)\]

def layout\_schnyder(G, face\_polygons=None) \-\> dict\[node, (x, y)\]

\# \=== SECTION 6: Generate Entry Point \===

def make\_graph\_entry(G\_base, pos, suffix, method\_name, extra\_meta=None) \-\> nx.Graph

def generate(input\_dir, output\_dir, \*\*kwargs) \-\> dict\[str, nx.Graph\]

### **4.3 Graph Metadata Schema**

Each graph entry stores in `G.graph`:

| Key | Type | Description |
| :---- | :---- | :---- |
| `name` | str | Display title, e.g. "Truncated Tetrahedron (Tutte)" use the McCooey name if it exists |
| `short_name` | str | Unique key, e.g. `polyhedra_truncated_tetrahedron_tutte` |
| `pos` | dict | 2D layout `{node: (x, y)}` for Manim rendering |
| `source` | str | `"polyhedra_3d"` |
| `embedding_method` | str | `"tutte"`, `"schramm"`, or `"schnyder"` |
| `3d_coordinates` | dict | `{node: (x, y, z)}` — from lift/packing (if computed) or mccooey if not computed |
| `face_polygons` | list | Face cycles `[[v0, v1, v2], ...]` |
| `face_count` | int | Number of polyhedral faces (V \- E \+ F \= 2\) |
| `face_colors` | dict | `{face_index: color_index}` — pre-computed 4-coloring |
| `vertex_configuration` | str | Schläfli-like, e.g. `"3.6.6"` (where applicable) |
| `symmetry_group` | str | Point group, e.g. `"Oh"`, `"Td"`, `"Ih"` (where known) |
| `is_convex_polyhedron` | bool | True for all qualifying graphs (by Steinitz) |
| `original_graph_key` | str | Source key from `all_planar_graphs.pkl` |

### **4.4 Naming Convention**

Every graph key is: `[category]_[name]_[method]`

**Examples:**

polyhedra\_tetrahedron\_tutte

polyhedra\_tetrahedron\_schramm

polyhedra\_tetrahedron\_schnyder

polyhedra\_truncated\_icosahedron\_tutte     (soccer ball / C60)

polyhedra\_truncated\_icosahedron\_schramm

polyhedra\_truncated\_icosahedron\_schnyder

kempe\_fritsch\_tutte

kempe\_fritsch\_schramm

kempe\_fritsch\_schnyder

RSST\_001\_tutte

RSST\_001\_schramm

RSST\_001\_schnyder

### **4.5 2D Projection Methods**

Each 3D method produces a 2D layout differently:

| Method | 3D → 2D Projection | Character |
| :---- | :---- | :---- |
| `_tutte` | Isometric: `x_2d = x - z*0.5`, `y_2d = y + z*0.3` | Convex faces visible, architectural feel |
| `_schramm` | Stereographic: project sphere to plane from south pole | Conformal, circles stay circular |
| `_schnyder` | Direct: barycentric → Cartesian in equilateral triangle | Grid-aligned, integer coordinates |

All layouts are passed through `normalize_pos()` from `base_module.py` to fit the Manim content area (7.50 wide × 5.75 tall).

---

## **5\. Auxiliary Triangulation — Shared Utility**

Several graphs (cube, dodecahedron, Archimedean solids, Catalan solids) have non-triangular faces. Both the Tutte lifting and Schnyder wood algorithms require triangulations. The solution is **temporary fan triangulation**:

**Step 1 — Triangulate:** For each face `(v0, v1, ..., vk)`, add edges `(v0, v2), (v0, v3), ..., (v0, v_{k-1})`.

Original hexagonal face:        Fan triangulation:

    v1 \--- v2                      v1 \--- v2

   /         \\                    /|  ╲      \\

  v0          v3        →       v0  |   ╲     v3

   \\         /                    \\|     ╲   /

    v5 \--- v4                      v5 \--- v4

                                 (add edges v0-v2, v0-v3, v0-v4)

**Step 2 — Compute layout** on the triangulated graph (Tutte lift or Schnyder wood).

**Step 3 — Remove auxiliary edges.** Vertex coordinates are unchanged. For Tutte lifts, convexity guarantees the original face vertices remain coplanar after diagonal removal. For Schnyder layouts, the grid positions are stable.

**Step 4 — Recompute face data** from original face lists and the now-known coordinates.

**When needed vs. not:**

| Graph Type | Already Triangulated? | Needs Auxiliary Step? |
| :---- | :---- | :---- |
| Kempe counterexamples | YES | No |
| RSST configurations | YES (mostly) | Possibly, check if G is 3-connected |
| Tetrahedron, Octahedron, Icosahedron | YES | No |
| Cube, Dodecahedron | No | YES |
| Archimedean / Catalan / Johnson solids | No | YES |

Circle packing (`_schramm`) does NOT require triangulation — it works on any 3-connected planar graph directly. So auxiliary triangulation is only invoked for `_tutte` and `_schnyder` pipelines.

---

## **6\. McCooey Scraper — Phase 0 Utility**

### **6.1 Scraper Script: `scrape_mccooey.py`**

A standalone pre-processing script that:

1. Downloads `.txt` files for all \~146 target convex polyhedra  
2. Parses constants, vertices (3D), and faces  
3. Builds NetworkX graphs with edges inferred from face adjacency  
4. Stores exact 3D coordinates and face polygons as metadata  
5. Verifies Euler's formula (V \- E \+ F \= 2\) and 3-connectivity  
6. Saves to `mccooey_polyhedra.pkl`

### **6.2 Parser Core**

import re

def parse\_mccooey\_txt(text: str) \-\> dict:

    lines \= text.strip().split('\\n')

    name \= lines\[0\].strip()

    constants \= {}

    vertices \= {}

    faces \= \[\]

    

    for line in lines\[1:\]:

        line \= line.strip()

        if not line:

            continue

        \# Constants: "C0 \= 1.175... \= 3 \* (15 \+ sqrt(5)) / 44"

        m \= re.match(r'(C\\d+)\\s\*=\\s\*(\[\\d.eE+-\]+)', line)

        if m:

            constants\[m.group(1)\] \= float(m.group(2))

            continue

        \# Vertices: "V0 \= ( expr, expr, expr )"

        m \= re.match(r'(V\\d+)\\s\*=\\s\*\\(\\s\*(.+?)\\s\*,\\s\*(.+?)\\s\*,\\s\*(.+?)\\s\*\\)', line)

        if m:

            coords \= \[\]

            for expr in \[m.group(2), m.group(3), m.group(4)\]:

                expr \= expr.strip()

                for cname, cval in sorted(constants.items(),

                        key=lambda x: \-len(x\[0\])):  \# longest first

                    expr \= expr.replace(cname, str(cval))

                coords.append(eval(expr))

            vertices\[m.group(1)\] \= tuple(coords)

            continue

        \# Faces: "{5} V0 V6 V54 V42 V8"

        m \= re.match(r'\\{(\\d+)\\}\\s+(.+)', line)

        if m:

            face\_verts \= \[v.strip() for v in m.group(2).split()\]

            faces.append(face\_verts)

    

    return {'name': name, 'constants': constants,

            'vertices': vertices, 'faces': faces}

### **6.3 URL Pattern**

https://dmccooey.com/polyhedra/Tetrahedron.txt

https://dmccooey.com/polyhedra/Cube.txt

https://dmccooey.com/polyhedra/TruncatedTetrahedron.txt

https://dmccooey.com/polyhedra/Cuboctahedron.txt

https://dmccooey.com/polyhedra/SnubCube.txt

...

The HTML name in the URL matches the `.html` page name with `.txt` extension. A master list of target polyhedra (the \~146 convex ones) is hardcoded in the scraper.

---

## **7\. Implementation Plan**

### **Phase 0: McCooey Scraper**

- Write `scrape_mccooey.py`  
- Download and parse \~146 convex polyhedra `.txt` files  
- Build NetworkX graphs with exact 3D coordinates  
- Verify Euler's formula and 3-connectivity  
- Save `mccooey_polyhedra.pkl`  
- **Output:** Ready-to-use graph dict with analytic 3D coordinates and face data

### **Phase 1: Tutte Pipeline (`_tutte`)**

- Implement `tutte_embedding()` — barycentric linear system solver  
- Implement `compute_equilibrium_stress()` — stress from Tutte positions  
- Implement `maxwell_cremona_lift()` — z-coordinates from stress  
- Implement `auxiliary_triangulate()` / `remove_auxiliary_edges()` — shared utility  
- Implement isometric 2D projection  
- Apply to all three tiers (McCooey, Kempe, RSST)  
- **Test:** Compare Tutte lift of Platonic solids against McCooey analytic coordinates

### **Phase 2: Schramm Pipeline (`_schramm`)**

- Implement `circle_packing_radii()` — iterative radius adjustment  
- Implement `place_circles_on_sphere()` — Möbius placement  
- Implement stereographic 2D projection  
- Apply to all three tiers  
- **Test:** Verify tangency conditions numerically; compare Platonic solids against known midsphere radii

### **Phase 3: Schnyder Pipeline (`_schnyder`)**

- Implement `compute_schnyder_wood()` — three-tree edge decomposition  
- Implement `schnyder_coordinates()` — region-counting for barycentric coords  
- Implement `barycentric_to_cartesian()` — project to 2D  
- Handle non-triangulations via auxiliary triangulation \+ post-removal  
- Apply to all three tiers  
- **Test:** Verify all coordinates are non-negative integers summing to n-1

### **Phase 4: Integration & Polish**

- Implement `face_four_coloring()` — greedy coloring of dual graph  
- Add all metadata fields to every graph entry  
- Register module in `generate_planar_pkls.py`  
- Ensure all `pos` dicts pass through `normalize_pos()`  
- Verify compatibility with `coloring_animation.py`  
- Log summary: graphs processed, skipped (with reasons), timings per method

---

## **8\. Key Design Decisions**

### **Q: Why implement all three methods instead of just one?**

**A:** Each method reveals different mathematical structure. Tutte shows the convex-face property and Maxwell's stress theory. Schramm shows the deep connection between circle packing, conformal geometry, and polyhedra. Schnyder shows the integer-grid embedding theorem and tree decompositions. For a senior project on the Four Color Theorem, demonstrating that these three independent mathematical traditions all produce valid planar embeddings — and that all of them can be 4-colored — is a powerful narrative. The visual differences between layouts are striking and make for excellent presentation slides.

### **Q: How do we handle graphs that aren't 3-connected?**

**A:** Skip them with a log message. Steinitz's theorem says they have no convex polyhedral realization, so excluding them is mathematically correct. The module logs which RSST configurations failed and why.

### **Q: What about the compile time?**

**A:** With \~785 base graphs × 3 methods, assuming worst-case 10 seconds per (graph, method) pair for circle packing, the total is \~6.5 hours. In practice, most graphs are small (\< 50 vertices) and will compute in under 1 second each. Tutte and Schnyder are both near-instant (sparse linear solve and linear-time tree traversal). Only Schramm's iterative circle packing takes meaningful time. A realistic estimate is 30–60 minutes total.

### **Q: Should we generate dual graphs?**

**A:** Yes, as computed metadata. The face 4-coloring requires the dual graph anyway. `face_polygons` implicitly defines the dual. The actual dual graph object can be computed on demand for any entry.

### **Q: What about the `all_planar_graphs.pkl` input dependency?**

**A:** The module looks for the combined pickle in `output_dir`. If it doesn't exist, the module generates only the McCooey polyhedra layouts (which are self-contained via `mccooey_polyhedra.pkl`). This way Phase 0 \+ Phase 1–3 can run independently.

---

## **9\. Registration**

\# In generate\_planar\_pkls.py MODULE\_REGISTRY:

("modules.generate\_3D\_graphs", "polyhedra\_3d", False),

`needs_input_dir=False` because McCooey polyhedra are self-contained. The module optionally loads `all_planar_graphs.pkl` from `output_dir` for Kempe and RSST graphs.

---

## **10\. Famous Polyhedra Reference**

### **Platonic Solids (5)**

| Name | V | E | F | Vertex Config | Schläfli | Symmetry |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Tetrahedron | 4 | 6 | 4 | 3.3.3 | {3,3} | Td |
| Cube | 8 | 12 | 6 | 4.4.4 | {4,3} | Oh |
| Octahedron | 6 | 12 | 8 | 3.3.3.3 | {3,4} | Oh |
| Dodecahedron | 20 | 30 | 12 | 5.5.5 | {5,3} | Ih |
| Icosahedron | 12 | 30 | 20 | 3.3.3.3.3 | {3,5} | Ih |

### **Archimedean Solids (13)**

Truncated Tetrahedron (3.6.6), Cuboctahedron (3.4.3.4), Truncated Octahedron (4.6.6), Truncated Cube (3.8.8), Rhombicuboctahedron (3.4.4.4), Snub Cube (3.3.3.3.4), Icosidodecahedron (3.5.3.5), Truncated Cuboctahedron (4.6.8), Truncated Icosahedron (5.6.6), Truncated Dodecahedron (3.10.10), Rhombicosidodecahedron (3.4.5.4), Snub Dodecahedron (3.3.3.3.5), Truncated Icosidodecahedron (4.6.10).

All are 3-connected. All have exact coordinates available from McCooey. The truncated icosahedron (soccer ball / C60 fullerene) is particularly relevant for the 4CT presentation.

---

## **11\. References**

- **Steinitz, E.** (1922). "Polyeder und Raumeinteilungen." *Encyclopädie der mathematischen Wissenschaften*, Band 3\.  
- **Tutte, W. T.** (1963). "How to draw a graph." *Proc. London Math. Soc.* 13, 743–768.  
- **Maxwell, J. C.** (1864). "On reciprocal figures and diagrams of forces." *Phil. Mag.* 27, 250–261.  
- **Schnyder, W.** (1990). "Embedding Planar Graphs on the Grid." *SODA '90*, 138–148. \[In project: `Embedding_Planar_Graphs_on_the_Grid__Walter_Schnyder.pdf`\]  
- **Schramm, O.** (1992). "How to cage an egg." *Inventiones Mathematicae* 107, 543–560. \[In project: `How_to_cage_an_egg__Oded_Schramm.pdf`\]  
- **Mohar, B.** (1993). "A polynomial time circle packing algorithm." *Discrete Mathematics* 117, 257–263.  
- **Robertson, Sanders, Seymour, Thomas** (1997). "The Four-Colour Theorem." \[In project: multiple PDFs\]  
- **Gonthier, G.** (2008). "Formal Proof — The Four Color Theorem." \[In project: `Formal_Proof__The_Four_Color_Theorem__Gonthier.pdf`\]  
- **Rote, G.** "Realizing Planar Graphs as Convex Polytopes." — Maxwell-Cremona correspondence details.  
- **McCooey, D.** "Visual Polyhedra." `https://dmccooey.com/polyhedra/` — 767+ polyhedra with exact 3D coordinates.  
- **Baranek, A. & Belen, L.** "Rpolyhedra: A Polyhedra Database." `https://github.com/ropensci/Rpolyhedra` — R package scraping McCooey's database (MIT license).
