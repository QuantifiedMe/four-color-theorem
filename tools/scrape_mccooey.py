#!/usr/bin/env python3
"""
scrape_mccooey.py
=================
Scrapes convex polyhedra data from David McCooey's Visual Polyhedra website
(https://dmccooey.com/polyhedra/) and exports structured CSV files for
downstream processing in the Four Color Theorem graph library.

Targets ~146 convex polyhedra across 6 categories:
    - 5  Platonic solids
    - 16 Archimedean solids  (includes L/R snub variants)
    - 15 Catalan solids      (duals of Archimedean)
    - 92 Johnson solids
    - ~12 Prisms/Antiprisms  (convex n-gonal, n = 3..12)

Output files (written to --output-dir):
    mccooey_polyhedra.csv  — one row per polyhedron (summary metrics)
    mccooey_vertices.csv   — one row per vertex     (polyhedron, id, x, y, z)
    mccooey_faces.csv      — one row per face        (polyhedron, id, n_sides, vertex_ids)

Safe to re-run: appends new rows, skips polyhedra already in the CSVs.
Use --overwrite to delete existing CSVs and start fresh.

Usage:
    python scrape_mccooey.py                                # Scrape all, default output
    python scrape_mccooey.py --categories platonic johnson   # Specific categories only
    python scrape_mccooey.py --output-dir ./data             # Custom output directory
    python scrape_mccooey.py --dry-run                       # Discover names only, no download
    python scrape_mccooey.py --overwrite                     # Delete existing CSVs first
    python scrape_mccooey.py --verbose                       # Debug-level logging
    python scrape_mccooey.py --https                         # Use HTTPS instead of HTTP
    python scrape_mccooey.py --no-verify-ssl                 # Disable SSL cert verification
    python scrape_mccooey.py --https --no-verify-ssl         # HTTPS + skip SSL (corp networks)

Known issue — garbled downloads:
    On some networks (corporate proxies, university firewalls), ~15 of the
    ~139 .txt files arrive as garbled binary instead of plain text.  The
    affected polyhedra were parsed manually from the McCooey website and
    appended to the CSVs by hand.  They are listed below so future users
    can verify their CSVs contain them.

    Manually parsed polyhedra (16 total):
        Platonic:        Dodecahedron
        Archimedean:     Cuboctahedron, TruncatedCube, Rhombicuboctahedron,
                         TruncatedIcosahedron, Rhombicosidodecahedron,
                         LsnubDodecahedron
        Catalan:         DeltoidalIcositetrahedron, LpentagonalIcositetrahedron,
                         RhombicTriacontahedron, DisdyakisTriacontahedron
        Johnson:         SquarePyramid (J1), SnubDisphenoid (J84),
                         AugmentedSphenocorona (J87), Sphenomegacorona (J88),
                         ElongatedSquareGyrobicupola (J37)

Dependencies:
    pip install requests beautifulsoup4

Project layout:
    repos/four-color-theorem/tools/scrape_mccooey.py        <- this script
    repos/four-color-theorem/graph_library/input/            <- default output dir

Author:  Tanya Wilcox — MTH-392 Senior Project, Wilkes University, Spring 2026
License: MIT
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import OrderedDict
from pathlib import Path

# Some polyhedra have large edge_list_json fields that exceed Python's
# default CSV field size limit (131072 bytes).  Use a safe cross-platform
# value — sys.maxsize overflows the C long on Windows.
csv.field_size_limit(10_000_000)

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required.  Install with:  pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: 'beautifulsoup4' package required.  Install with:  pip install beautifulsoup4")
    sys.exit(1)


# ============================================================
# Constants
# ============================================================

BASE_URL = "http://dmccooey.com/polyhedra"  # HTTP — avoids SSL issues on corporate networks
BASE_URL_HTTPS = "https://dmccooey.com/polyhedra"

# Category index pages → (page_url_suffix, category_label)
# The scraper fetches each index page and extracts polyhedron links.
CATEGORY_PAGES = {
    "platonic": [
        ("Platonic.html", "Platonic")
    ],
    "archimedean": [
        ("Archimedean.html", "Archimedean")
    ],
    "catalan": [
        ("Catalan.html", "Catalan")
    ],
    "johnson": [
        ("JohnsonPage1.html", "Johnson"),
        ("JohnsonPage2.html", "Johnson"),
        ("JohnsonPage3.html", "Johnson"),
        ("JohnsonPage4.html", "Johnson"),
        ("JohnsonPage5.html", "Johnson"),
    ],
    "prism": [
        ("PrismAntiprism.html", "Prism/Antiprism")
    ],
}

# For Prisms/Antiprisms the index page contains BOTH prisms and antiprisms
# plus star variants we don't want.  We filter by name prefix.
PRISM_TARGETS = {
    # n-gonal prisms (convex, n = 3..12)
    "TriangularPrism", "SquarePrism", "PentagonalPrism", "HexagonalPrism",
    "HeptagonalPrism", "OctagonalPrism", "NonagonalPrism", "DecagonalPrism",
    "HendecagonalPrism", "DodecagonalPrism",
    # n-gonal antiprisms (convex, n = 3..12)
    "TriangularAntiprism", "SquareAntiprism", "PentagonalAntiprism",
    "HexagonalAntiprism", "HeptagonalAntiprism", "OctagonalAntiprism",
    "NonagonalAntiprism", "DecagonalAntiprism", "HendecagonalAntiprism",
    "DodecagonalAntiprism",
}

# Polite delay between HTTP requests (seconds)
REQUEST_DELAY = 0.4

# HTTP session settings
TIMEOUT = 30
MAX_RETRIES = 3

LOG = logging.getLogger("scrape_mccooey")


# ============================================================
# HTTP helpers
# ============================================================

def make_session(verify_ssl=True):
    """Create a requests.Session with retry logic and a polite User-Agent."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "McCooey-Polyhedra-Scraper/1.0 "
            "(Four Color Theorem Senior Project; "
            "contact: academic research use only)"
        ),
    })
    session.verify = verify_ssl
    return session


def fetch_url(session, url, retries=MAX_RETRIES):
    """Fetch a URL with retries and polite delay.  Returns text or None."""
    for attempt in range(1, retries + 1):
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            LOG.warning("  Attempt %d/%d failed for %s: %s", attempt, retries, url, e)
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff
    LOG.error("  FAILED after %d attempts: %s", retries, url)
    return None


# ============================================================
# Discovery — find polyhedra names from category index pages
# ============================================================

def discover_polyhedra_from_index(session, page_url, category, filter_set=None):
    """
    Scrape a McCooey category index page and extract polyhedron names.

    Returns list of dicts: [{"url_stem": "TruncatedTetrahedron",
                              "display_name": "Truncated Tetrahedron",
                              "category": "Archimedean",
                              "johnson_number": None or "J12"}, ...]
    """
    html = fetch_url(session, page_url)
    if html is None:
        LOG.error("Could not fetch index page: %s", page_url)
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Match links like "TruncatedTetrahedron.html" but not external links
        m = re.match(r'^([A-Z][A-Za-z0-9]+)\.html$', href)
        if not m:
            continue

        url_stem = m.group(1)

        # Skip navigation links to other index pages
        skip_stems = {
            "Platonic", "Archimedean", "Catalan", "Johnson",
            "JohnsonPage1", "JohnsonPage2", "JohnsonPage3",
            "JohnsonPage4", "JohnsonPage5",
            "PrismAntiprism", "StarPrismAntiprism",
            "DipyramidTrapezohedron", "StarDipyramidTrapezohedron",
        }
        if url_stem in skip_stems:
            continue

        # For Prism/Antiprism page: filter to only convex targets
        if filter_set and url_stem not in filter_set:
            continue

        display_name = link.get_text(strip=True)
        if not display_name:
            display_name = url_stem

        # Extract Johnson number if present in nearby text
        johnson_number = None
        parent_text = link.parent.get_text() if link.parent else ""
        jm = re.search(r'\(J(\d+)\)', parent_text)
        if jm:
            johnson_number = f"J{jm.group(1)}"

        results.append({
            "url_stem":       url_stem,
            "display_name":   display_name,
            "category":       category,
            "johnson_number": johnson_number,
        })

    LOG.info("  Discovered %d polyhedra from %s", len(results), page_url)
    return results


def discover_all(session, categories):
    """
    Discover all target polyhedra across the requested categories.
    Returns a list of info dicts (deduplicated by url_stem).
    """
    seen = set()
    all_poly = []

    for cat_key in categories:
        if cat_key not in CATEGORY_PAGES:
            LOG.warning("Unknown category '%s' — skipping", cat_key)
            continue

        for page_suffix, label in CATEGORY_PAGES[cat_key]:
            page_url = f"{BASE_URL}/{page_suffix}"
            filter_set = PRISM_TARGETS if cat_key == "prism" else None
            entries = discover_polyhedra_from_index(
                session, page_url, label, filter_set
            )
            for entry in entries:
                if entry["url_stem"] not in seen:
                    seen.add(entry["url_stem"])
                    all_poly.append(entry)

    LOG.info("Total unique polyhedra discovered: %d", len(all_poly))
    return all_poly


# ============================================================
# Parser — parse McCooey .txt coordinate files
# ============================================================

def parse_mccooey_txt(text):
    """
    Parse a McCooey .txt coordinate file.

    Format (actual, from dmccooey.com):
        Line 1:         Polyhedron Name
        Constants block: C0 = 1.234... = symbolic_expr
        Vertices block:  V0 = ( expr, expr, expr )
        Faces header:    Faces:
        Faces block:     { 0, 2, 4 }       ← numeric vertex indices, comma-separated

    Returns dict with keys:
        name, constants, vertices, faces, raw_text
    Or None if parsing fails.
    """
    lines = text.strip().split('\n')
    if not lines:
        return None

    name = lines[0].strip()
    constants = OrderedDict()   # C0 -> float  (ordered for correct substitution)
    vertices = OrderedDict()    # "V0" -> (x, y, z)
    faces = []                  # [{"n_sides": 5, "vertex_ids": ["V0","V6",...]}, ...]
    in_faces_block = False      # True once we see the "Faces:" header

    # Build ordered vertex-id list for numeric index → V-name mapping
    vertex_order = []           # filled as V0, V1, ... are parsed

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # --- Detect "Faces:" header (marks start of face block) ---
        if re.match(r'^Faces\s*:', line):
            in_faces_block = True
            continue

        # --- Parse constant definitions ---
        # "C0  = 1.17518645301134929748244365923  = 3 * (15 + sqrt(5)) / 44"
        # Some simple polyhedra have no constants at all.
        if not in_faces_block:
            m = re.match(
                r'(C\d+)\s*=\s*([0-9eE.+-]+(?:\.\d*)?)',
                line
            )
            if m:
                cname = m.group(1)
                try:
                    cval = float(m.group(2))
                except ValueError:
                    LOG.warning("  Could not parse constant value: %s", line)
                    continue
                constants[cname] = cval
                continue

        # --- Parse vertex definitions ---
        # "V0   = ( 0.0,  0.0,  C18)"
        if not in_faces_block:
            m = re.match(
                r'(V\d+)\s*=\s*\(\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)',
                line
            )
            if m:
                vid = m.group(1)
                coords = []
                parse_ok = True
                for expr_raw in [m.group(2), m.group(3), m.group(4)]:
                    expr = expr_raw.strip()
                    val = _eval_coord_expr(expr, constants)
                    if val is None:
                        LOG.warning("  Could not evaluate coordinate '%s' in %s", expr, vid)
                        parse_ok = False
                        break
                    coords.append(val)
                if parse_ok:
                    vertices[vid] = tuple(coords)
                    vertex_order.append(vid)
                continue

        # --- Parse face definitions ---
        # Format A (standard): "{ 0, 2, 4 }" or "{ 0, 2, 14, 4, 12 }"
        #   Numeric indices, comma-separated, in curly braces.
        #   Index n maps to vertex V{n} by order of appearance.
        m = re.match(r'\{\s*(.+?)\s*\}', line)
        if m:
            inner = m.group(1).strip()
            # Check if comma-separated numbers (Format A)
            if ',' in inner:
                parts = [p.strip() for p in inner.split(',')]
                face_verts = []
                for p in parts:
                    try:
                        idx = int(p)
                        # Map numeric index to V-name
                        if idx < len(vertex_order):
                            face_verts.append(vertex_order[idx])
                        else:
                            face_verts.append(f"V{idx}")
                    except ValueError:
                        # Maybe already a V-name?
                        face_verts.append(p)
                faces.append({
                    "n_sides":    len(face_verts),
                    "vertex_ids": face_verts,
                })
                continue

        # Format B (rare, some derived solids): "{5}  V0  V6  V54  V42  V8"
        #   Polygon-count prefix, then V-prefixed names, space-separated.
        m = re.match(r'\{(\d+)\}\s+(.+)', line)
        if m:
            face_verts = [v.strip() for v in m.group(2).split() if v.strip()]
            faces.append({
                "n_sides":    len(face_verts),
                "vertex_ids": face_verts,
            })
            continue

    if not vertices:
        LOG.warning("  No vertices parsed from file")
        return None

    return {
        "name":      name,
        "constants": constants,
        "vertices":  vertices,
        "faces":     faces,
        "raw_text":  text,
    }


def _eval_coord_expr(expr, constants):
    """
    Evaluate a coordinate expression like '0.5', 'C3', '-C17',
    or arithmetic combos like 'C1 + 0.5'.

    Uses constant substitution then safe eval (only numbers & arithmetic).
    Returns float or None on failure.
    """
    expr = expr.strip()

    # Substitute constant names with their float values.
    # Sort by name length descending so C17 is replaced before C1.
    for cname in sorted(constants.keys(), key=lambda k: -len(k)):
        expr = expr.replace(cname, repr(constants[cname]))

    # Safety: only allow digits, decimal points, +, -, *, /, parens, spaces, 'e'
    if not re.match(r'^[\d.eE+\-*/() ]+$', expr):
        return None

    try:
        return float(eval(expr))  # safe: only arithmetic on floats
    except Exception:
        return None


# ============================================================
# Metric computation
# ============================================================

def compute_metrics(parsed):
    """
    Compute V, E, F and Euler characteristic from parsed polyhedron data.
    Also extracts the set of edges from face definitions.

    Returns dict with: V, E, F, euler_char, edges (set of sorted tuples)
    """
    V = len(parsed["vertices"])
    F = len(parsed["faces"])

    # Build edge set from faces
    edges = set()
    vid_list = list(parsed["vertices"].keys())

    for face in parsed["faces"]:
        vids = face["vertex_ids"]
        for i in range(len(vids)):
            v1 = vids[i]
            v2 = vids[(i + 1) % len(vids)]
            edge = tuple(sorted([v1, v2]))
            edges.add(edge)

    E = len(edges)
    euler = V - E + F

    return {
        "V": V,
        "E": E,
        "F": F,
        "euler_char": euler,
        "edges": edges,
    }


def vertex_configuration_string(parsed, vertex_id):
    """
    Compute the vertex configuration string for a given vertex.
    This is the sorted cycle of face-sizes meeting at that vertex (e.g., "3.4.3.4").
    Returns the string or "" if undetermined.
    """
    face_sizes = []
    for face in parsed["faces"]:
        if vertex_id in face["vertex_ids"]:
            face_sizes.append(face["n_sides"])
    if not face_sizes:
        return ""
    face_sizes.sort()
    return ".".join(str(n) for n in face_sizes)


# ============================================================
# CSV output
# ============================================================

POLY_HEADER = [
    "url_stem", "name", "category", "johnson_number",
    "vertices", "edges", "faces", "euler_characteristic",
    "vertex_configuration", "edge_list_json",
]
VERT_HEADER = ["polyhedron", "vertex_id", "x", "y", "z"]
FACE_HEADER = ["polyhedron", "face_id", "n_sides", "vertex_ids"]


def load_existing_stems(output_dir):
    """
    Check for existing mccooey_polyhedra.csv and return the set of
    url_stems already present.  Returns empty set if file doesn't exist.

    Reads url_stem (first column) directly from raw lines to avoid
    csv.DictReader choking on large edge_list_json fields.
    """
    poly_path = os.path.join(output_dir, "mccooey_polyhedra.csv")
    stems = set()
    if not os.path.exists(poly_path):
        return stems
    try:
        with open(poly_path, "rb") as f:
            first_line = True
            for raw_line in f:
                if first_line:
                    first_line = False
                    continue  # skip header
                # url_stem is the first column — grab everything before the first comma
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    stem = line.split(",", 1)[0].strip().strip('"')
                    if stem:
                        stems.add(stem)
        LOG.info("  Loaded %d existing url_stems from %s", len(stems), poly_path)
    except Exception as e:
        LOG.warning("  Could not read existing CSV (%s) — treating as empty", e)
        stems.clear()
    return stems


def write_csvs(new_data, output_dir):
    """
    Append new polyhedra data to the three CSV files.

    - If a CSV doesn't exist yet, creates it with a header row.
    - If it already exists, appends new rows (no header re-written).
    - Duplicates are prevented upstream (caller skips already-scraped stems),
      but as a safety net this function also checks before writing.

    new_data: list of dicts, each with keys:
        info     — discovery info (url_stem, display_name, category, johnson_number)
        parsed   — parser output (name, constants, vertices, faces)
        metrics  — computed metrics (V, E, F, euler_char, edges)
    """
    os.makedirs(output_dir, exist_ok=True)

    poly_path = os.path.join(output_dir, "mccooey_polyhedra.csv")
    vert_path = os.path.join(output_dir, "mccooey_vertices.csv")
    face_path = os.path.join(output_dir, "mccooey_faces.csv")

    # Determine which stems already exist (safety net against duplicates)
    existing_stems = load_existing_stems(output_dir)

    # Filter to truly new entries only
    entries_to_write = [
        entry for entry in new_data
        if entry["info"]["url_stem"] not in existing_stems
    ]

    if not entries_to_write:
        LOG.info("No new polyhedra to write — CSVs already up to date.")
        return poly_path, vert_path, face_path

    skipped = len(new_data) - len(entries_to_write)
    if skipped:
        LOG.info("  Skipping %d duplicate(s) already in CSVs", skipped)

    # --- Helper: open for append (write header only if file is new) ---
    def _open_csv(path, header):
        file_is_new = not os.path.exists(path) or os.path.getsize(path) == 0
        f = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(f)
        if file_is_new:
            writer.writerow(header)
        return f, writer

    # --- Polyhedra summary ---
    f, writer = _open_csv(poly_path, POLY_HEADER)
    for entry in entries_to_write:
        info = entry["info"]
        parsed = entry["parsed"]
        metrics = entry["metrics"]

        first_vid = list(parsed["vertices"].keys())[0] if parsed["vertices"] else ""
        vconfig = vertex_configuration_string(parsed, first_vid) if first_vid else ""

        edge_json = json.dumps(
            sorted([list(e) for e in metrics["edges"]]),
            separators=(',', ':')
        )

        writer.writerow([
            info["url_stem"],
            parsed["name"],
            info["category"],
            info["johnson_number"] or "",
            metrics["V"],
            metrics["E"],
            metrics["F"],
            metrics["euler_char"],
            vconfig,
            edge_json,
        ])
    f.close()
    LOG.info("Appended %d rows to %s", len(entries_to_write), poly_path)

    # --- Vertices ---
    vert_count = 0
    f, writer = _open_csv(vert_path, VERT_HEADER)
    for entry in entries_to_write:
        stem = entry["info"]["url_stem"]
        for vid, (x, y, z) in entry["parsed"]["vertices"].items():
            writer.writerow([stem, vid, f"{x:.15g}", f"{y:.15g}", f"{z:.15g}"])
            vert_count += 1
    f.close()
    LOG.info("Appended %d rows to %s", vert_count, vert_path)

    # --- Faces ---
    face_count = 0
    f, writer = _open_csv(face_path, FACE_HEADER)
    for entry in entries_to_write:
        stem = entry["info"]["url_stem"]
        for i, face in enumerate(entry["parsed"]["faces"]):
            vids_str = ";".join(face["vertex_ids"])
            writer.writerow([stem, f"F{i}", face["n_sides"], vids_str])
            face_count += 1
    f.close()
    LOG.info("Appended %d rows to %s", face_count, face_path)

    return poly_path, vert_path, face_path


# ============================================================
# Main pipeline
# ============================================================

def scrape_polyhedron(session, info):
    """
    Fetch and parse a single polyhedron's .txt file.
    Returns parsed dict or None on failure.
    """
    url = f"{BASE_URL}/{info['url_stem']}.txt"
    LOG.info("  Fetching %s ...", url)

    text = fetch_url(session, url)
    if text is None:
        return None

    parsed = parse_mccooey_txt(text)
    if parsed is None:
        LOG.warning("  Parse failed for %s", info["url_stem"])
        return None

    metrics = compute_metrics(parsed)

    if metrics["euler_char"] != 2:
        LOG.warning("  Euler check FAILED for %s: V=%d E=%d F=%d  χ=%d",
                    info["url_stem"], metrics["V"], metrics["E"],
                    metrics["F"], metrics["euler_char"])
    else:
        LOG.debug("  OK: %s  V=%d E=%d F=%d  χ=2 ✓",
                  info["url_stem"], metrics["V"], metrics["E"], metrics["F"])

    return {
        "info":    info,
        "parsed":  parsed,
        "metrics": metrics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape convex polyhedra data from dmccooey.com/polyhedra/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.path.join(os.path.dirname(__file__), "..", "graph_library", "input"),
        help="Directory for output CSV files (default: ../graph_library/input/)",
    )
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        default=list(CATEGORY_PAGES.keys()),
        choices=list(CATEGORY_PAGES.keys()),
        help="Which categories to scrape (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover polyhedra names; don't download .txt files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing CSVs and start fresh (default: append new, skip duplicates)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS instead of HTTP (default is HTTP to avoid SSL issues)",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (use with --https on corporate networks)",
    )
    args = parser.parse_args()

    # --- Logging setup ---
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # --- Configure base URL and SSL ---
    global BASE_URL
    if args.https:
        BASE_URL = BASE_URL_HTTPS
        LOG.info("Using HTTPS")
    if args.no_verify_ssl:
        LOG.warning("SSL certificate verification DISABLED")
        # Suppress the urllib3 InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    output_dir = os.path.abspath(args.output_dir)
    LOG.info("Output directory: %s", output_dir)
    LOG.info("Categories: %s", ", ".join(args.categories))

    # --- Discover polyhedra ---
    verify_ssl = not args.no_verify_ssl
    session = make_session(verify_ssl=verify_ssl)

    LOG.info("=== Phase 1: Discovering polyhedra from index pages ===")
    all_poly_info = discover_all(session, args.categories)

    if not all_poly_info:
        LOG.error("No polyhedra discovered — check network connectivity and category names.")
        sys.exit(1)

    LOG.info("")
    LOG.info("Discovered %d polyhedra:", len(all_poly_info))
    for cat in sorted(set(p["category"] for p in all_poly_info)):
        count = sum(1 for p in all_poly_info if p["category"] == cat)
        LOG.info("  %-20s %d", cat, count)

    if args.dry_run:
        LOG.info("")
        LOG.info("--- Dry run: listing discovered polyhedra ---")
        for p in all_poly_info:
            jn = f" ({p['johnson_number']})" if p["johnson_number"] else ""
            LOG.info("  [%s] %s%s", p["category"], p["display_name"], jn)
        LOG.info("Done (dry run).  Would scrape %d .txt files.", len(all_poly_info))
        return

    # --- Overwrite mode: delete existing CSVs if requested ---
    if args.overwrite:
        for fname in ["mccooey_polyhedra.csv", "mccooey_vertices.csv", "mccooey_faces.csv"]:
            fpath = os.path.join(output_dir, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
                LOG.info("  Deleted existing %s", fpath)

    # --- Check existing CSVs for already-scraped polyhedra ---
    already_scraped = load_existing_stems(output_dir)
    if already_scraped:
        LOG.info("Found %d polyhedra already in CSVs — will skip these", len(already_scraped))

    # --- Scrape .txt files (skip duplicates) ---
    LOG.info("")
    LOG.info("=== Phase 2: Downloading and parsing .txt coordinate files ===")

    all_data = []
    failed = []
    skipped = 0
    for i, info in enumerate(all_poly_info, 1):
        if info["url_stem"] in already_scraped:
            LOG.debug("  [%d/%d] SKIP (already in CSV): %s",
                      i, len(all_poly_info), info["url_stem"])
            skipped += 1
            continue

        LOG.info("[%d/%d] %s (%s)",
                 i, len(all_poly_info), info["display_name"], info["category"])

        result = scrape_polyhedron(session, info)
        if result:
            all_data.append(result)
        else:
            failed.append(info["url_stem"])

    if skipped:
        LOG.info("  Skipped %d polyhedra already in CSVs", skipped)

    # --- Append to output CSVs ---
    LOG.info("")
    LOG.info("=== Phase 3: Writing CSV output ===")

    if all_data:
        poly_path, vert_path, face_path = write_csvs(all_data, output_dir)
    else:
        if skipped:
            LOG.info("All polyhedra already scraped — nothing new to write.")
        else:
            LOG.warning("No data to write!")

    # --- Summary ---
    total_in_csv = len(already_scraped) + len(all_data)
    LOG.info("")
    LOG.info("=" * 60)
    LOG.info("SCRAPE COMPLETE")
    LOG.info("  New polyhedra scraped:   %d", len(all_data))
    LOG.info("  Already in CSVs:         %d", len(already_scraped))
    LOG.info("  Total in CSVs now:       %d", total_in_csv)
    LOG.info("  Failed this run:         %d", len(failed))
    if failed:
        for stem in failed:
            LOG.info("    FAILED: %s", stem)

    euler_ok = sum(1 for d in all_data if d["metrics"]["euler_char"] == 2)
    euler_bad = len(all_data) - euler_ok
    LOG.info("  Euler check passed: %d", euler_ok)
    if euler_bad:
        LOG.warning("  Euler check FAILED: %d", euler_bad)
        for d in all_data:
            if d["metrics"]["euler_char"] != 2:
                m = d["metrics"]
                LOG.warning("    %s: V=%d E=%d F=%d χ=%d",
                            d["info"]["url_stem"], m["V"], m["E"], m["F"],
                            m["euler_char"])

    total_verts = sum(d["metrics"]["V"] for d in all_data)
    total_faces = sum(d["metrics"]["F"] for d in all_data)
    LOG.info("  Total vertices:     %d", total_verts)
    LOG.info("  Total faces:        %d", total_faces)
    LOG.info("  Output directory:   %s", output_dir)
    LOG.info("=" * 60)


if __name__ == "__main__":
    main()


