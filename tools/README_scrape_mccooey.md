# scrape_mccooey.py — McCooey Polyhedra Scraper

Utility script for the **Four Color Theorem** graph library project. Scrapes convex polyhedra data (3D vertex coordinates, face definitions, and graph metrics) from David McCooey's [Visual Polyhedra](https://dmccooey.com/polyhedra/) database and exports structured CSV files.

## Why this script exists

The [Rpolyhedra](https://github.com/ropensci/Rpolyhedra) R package already scraped all 767 polyhedra from McCooey's site, but requires an older R version incompatible with current R installations. This Python scraper reproduces the same extraction for our ~140 target convex polyhedra, outputting data in a portable CSV format that feeds directly into `generate_3D_graphs.py` (Phase 1–3 of the 3D Polyhedra Module).

## Scrape results (as of March 2026)

| Category | Discovered | Scraped | Manual | Total |
|---|---|---|---|---|
| Platonic | 5 | 4 | 1 | 5 |
| Archimedean | 16 | 10 | 6 | 16 |
| Catalan | 15 | 11 | 4 | 15 |
| Johnson | 91 | 87 | 5 | 92 |
| Prism/Antiprism | 12 | 12 | 0 | 12 |
| **Total** | **139** | **124** | **16** | **140** |

Final CSV: **139 unique polyhedra** (after deduplication). All pass Euler's formula (V − E + F = 2).

## Requirements

```
pip install requests beautifulsoup4
```

Python 3.8+. No other dependencies.

## Usage

```bash
python scrape_mccooey.py                                 # Scrape all, default output
python scrape_mccooey.py --categories platonic johnson   # Specific categories only
python scrape_mccooey.py --output-dir ./data             # Custom output directory
python scrape_mccooey.py --dry-run                       # Discover names only, no download
python scrape_mccooey.py --overwrite                     # Delete existing CSVs first
python scrape_mccooey.py --verbose                       # Debug-level logging
python scrape_mccooey.py --https                         # Use HTTPS instead of HTTP
python scrape_mccooey.py --no-verify-ssl                 # Disable SSL cert verification
python scrape_mccooey.py --https --no-verify-ssl         # HTTPS + skip SSL (corp networks)
```

## Append behavior (default)

The scraper is **safe to re-run**. On each invocation it reads `mccooey_polyhedra.csv` to find which `url_stem` values are already present, skips HTTP requests for those, and appends only new rows to all three CSV files. Partial scrapes accumulate into the same files. Use `--overwrite` to start fresh.

## Output files

The scraper writes three CSV files to the output directory:

### `mccooey_polyhedra.csv` — Summary (one row per polyhedron)

| Column | Type | Description |
|---|---|---|
| `url_stem` | str | McCooey URL key, e.g. `TruncatedTetrahedron` |
| `name` | str | Display name from the .txt file |
| `category` | str | `Platonic`, `Archimedean`, `Catalan`, `Johnson`, `Prism/Antiprism` |
| `johnson_number` | str | `J1`–`J92` for Johnson solids, blank otherwise |
| `vertices` | int | Vertex count (V) |
| `edges` | int | Edge count (E) |
| `faces` | int | Face count (F) |
| `euler_characteristic` | int | V − E + F (should always be 2) |
| `vertex_configuration` | str | Sorted face-sizes at first vertex, e.g. `3.6.6` |
| `edge_list_json` | str | JSON array of `[V_i, V_j]` edge pairs |

### `mccooey_vertices.csv` — Vertex coordinates (one row per vertex)

| Column | Type | Description |
|---|---|---|
| `polyhedron` | str | `url_stem` foreign key |
| `vertex_id` | str | `V0`, `V1`, ... |
| `x` | float | 3D x-coordinate (15 significant figures) |
| `y` | float | 3D y-coordinate |
| `z` | float | 3D z-coordinate |

### `mccooey_faces.csv` — Face definitions (one row per face)

| Column | Type | Description |
|---|---|---|
| `polyhedron` | str | `url_stem` foreign key |
| `face_id` | str | `F0`, `F1`, ... |
| `n_sides` | int | Number of sides (3=triangle, 4=square, etc.) |
| `vertex_ids` | str | Semicolon-separated vertex cycle, e.g. `V0;V1;V2` |

## How it works

### Phase 1: Discovery

Fetches each category's HTML index page from McCooey's site, extracts polyhedron names and URL stems via `<a href="...">` link parsing. For the Prism/Antiprism page, a whitelist filter keeps only convex n-gonal prisms and antiprisms (n=3–12), excluding star variants.

### Phase 2: Parsing

For each discovered polyhedron, downloads the corresponding `.txt` file. The McCooey `.txt` format contains:

1. **Constants block** — named floating-point values with optional symbolic expressions: `C0 = 1.307... = (3 + sqrt(5)) / 4`
2. **Vertices block** — 3D coordinates referencing constants by name: `V0 = ( C1, -C0, 0.0 )`
3. **Faces header** — the line `Faces:`
4. **Faces block** — vertex cycles as comma-separated numeric indices in braces: `{ 0, 2, 14, 4, 12 }`

The parser substitutes constant values into vertex expressions, evaluates them arithmetically, maps face indices to vertex IDs, builds the edge set from face adjacency, and verifies Euler's formula (V − E + F = 2) as a sanity check.

## Known issues and workarounds

### Garbled .txt downloads (16 polyhedra)

On our university network, approximately 16 of the ~139 `.txt` files consistently arrived as garbled binary (likely a proxy or firewall stripping `Content-Encoding` headers from compressed responses). Multiple workarounds were attempted including explicit `Accept-Encoding: identity` headers, `gzip`/`zlib`/`deflate` decompression, and `resp.content.decode()` fallbacks — none resolved the issue.

**Resolution:** The 16 affected polyhedra were parsed manually from `.txt` content copied directly from the McCooey website in a browser, then appended to the CSVs by hand. The manually parsed polyhedra are:

| Category | url_stem | Name |
|---|---|---|
| Platonic | Dodecahedron | Dodecahedron |
| Archimedean | Cuboctahedron | Cuboctahedron |
| Archimedean | TruncatedCube | Truncated Cube |
| Archimedean | Rhombicuboctahedron | Rhombicuboctahedron |
| Archimedean | TruncatedIcosahedron | Truncated Icosahedron |
| Archimedean | Rhombicosidodecahedron | Rhombicosidodecahedron |
| Archimedean | LsnubDodecahedron | Snub Dodecahedron (laevo) |
| Catalan | DeltoidalIcositetrahedron | Deltoidal Icositetrahedron |
| Catalan | LpentagonalIcositetrahedron | Pentagonal Icositetrahedron (laevo) |
| Catalan | RhombicTriacontahedron | Rhombic Triacontahedron |
| Catalan | DisdyakisTriacontahedron | Disdyakis Triacontahedron |
| Johnson | SquarePyramid | Square Pyramid (J1) |
| Johnson | SnubDisphenoid | Snub Disphenoid (J84) |
| Johnson | AugmentedSphenocorona | Augmented Sphenocorona (J87) |
| Johnson | Sphenomegacorona | Sphenomegacorona (J88) |
| Johnson | ElongatedSquareGyrobicupola | Elongated Square Gyrobicupola (J37) |

### SSL certificate errors

McCooey's site uses HTTPS, but some corporate/university networks intercept SSL traffic. The `--no-verify-ssl` flag disables certificate verification. The scraper defaults to HTTP to avoid this entirely.

### Discovery count (139 vs 146)

The scraper discovers 139 polyhedra from McCooey's index pages, slightly below the theoretical ~146 target. Some polyhedra may use non-standard URL stems or be listed on pages not covered by the scraper's category configuration. The 139 discovered include all 5 Platonic, all 13+ Archimedean, all 15 Catalan, 91 of 92 Johnson (J37 added manually), and 12 Prism/Antiprism.

## Downstream usage

```
scrape_mccooey.py → mccooey_*.csv → generate_3D_graphs.py → all_planar_graphs.pkl
                                     (Tutte / Schramm / Schnyder layouts)
```

To load the data in Python:

```python
import csv

with open("mccooey_polyhedra.csv") as f:
    polyhedra = list(csv.DictReader(f))

with open("mccooey_vertices.csv") as f:
    verts = {row["vertex_id"]: (float(row["x"]), float(row["y"]), float(row["z"]))
             for row in csv.DictReader(f)
             if row["polyhedron"] == "TruncatedTetrahedron"}

with open("mccooey_faces.csv") as f:
    faces = [row["vertex_ids"].split(";")
             for row in csv.DictReader(f)
             if row["polyhedron"] == "TruncatedTetrahedron"]

import networkx as nx
G = nx.Graph()
for vid, coords in verts.items():
    G.add_node(vid, pos_3d=coords)
for face in faces:
    for i in range(len(face)):
        G.add_edge(face[i], face[(i + 1) % len(face)])
```

## Data source

**McCooey, David I.** "Visual Polyhedra." https://dmccooey.com/polyhedra/

The `.txt` coordinate files are plain text served without an explicit license, but the data has been openly used by academic projects including [Rpolyhedra](https://github.com/ropensci/Rpolyhedra) (MIT license).

## Project context

- **Project:** Four Color Theorem Graph Library
- **Author:** Tanya Wilcox — MTH-392 Senior Project, Wilkes University, Spring 2026
- **Script location:** `repos/four-color-theorem/tools/scrape_mccooey.py`
- **Data location:** `repos/four-color-theorem/graph_library/input/mccooey_*.csv`

