"""
combine_algorithm_videos.py
===========================
Scans the Created Videos folder, groups videos by graph key,
and for each graph that has all 3 algorithm videos (Greedy, DSATUR, SmlLst),
stitches them side-by-side horizontally into one combined MP4.

Writes a sidecar JSON with graph + algorithm metadata so the quilt
script can filter/sort without re-probing anything.

Usage:
    python combine_algorithm_videos.py                  # dry-run (preview groups)
    python combine_algorithm_videos.py --run             # actually render
    python combine_algorithm_videos.py --run --algos Greedy DSATUR SmlLst Random
"""

import argparse
import subprocess
import json as _json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================================
# CONFIG — imported from centralized config.py
# ============================================================================
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from config import (
        VIDEO_CREATED_DIR, VIDEO_JSON_DIR, VIDEO_COMBINED_DIR,
        DEFAULT_ALGOS as _DEFAULT_ALGOS,
    )
    VIDEO_INPUT_DIR    = str(VIDEO_CREATED_DIR)
    JSON_INPUT_DIR     = str(VIDEO_JSON_DIR)
    COMBINED_OUTPUT_DIR = str(VIDEO_COMBINED_DIR)
    DEFAULT_ALGOS      = _DEFAULT_ALGOS
except ImportError:
    VIDEO_INPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\Created Videos"
    )
    JSON_INPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\JSON Files"
    )
    COMBINED_OUTPUT_DIR = (
        r"C:\Users\WWO8244\OneDrive - MDLZ\Senior Project"
        r"\Spring\Code\Video Output\Combined Videos"
    )
    DEFAULT_ALGOS = ["Greedy", "DSATUR", "SmlLst"]


# ============================================================================
# FILENAME PARSING
# ============================================================================

def parse_video_filename(filename: str):
    """
    Parse a filename like:
        RSST_042_Greedy_20250301T143022.mp4
        kempe_fritsch_1_DSATUR_20250301T143055.mp4

    Returns (graph_key, algo_name, datetime, timestamp_str)
    or (None, None, None, None).
    """
    stem = Path(filename).stem

    known_algos = {"Greedy", "DSATUR", "SmlLst", "Random"}
    parts = stem.split("_")

    if len(parts) < 3:
        return None, None, None, None

    timestamp_str = parts[-1]
    algo_candidate = parts[-2]

    if algo_candidate not in known_algos:
        return None, None, None, None

    try:
        dt = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
    except ValueError:
        return None, None, None, None

    graph_key = "_".join(parts[:-2])
    return graph_key, algo_candidate, dt, timestamp_str


# ============================================================================
# PER-RUN JSON LOADER
# ============================================================================

def load_run_json(json_dir: Path, graph_key: str, algo: str, timestamp_str: str):
    """
    Try to load the per-run JSON written by new_manim_scene.py.
    Filename pattern: {graph_key}_{algo}_{timestamp}.json
    Returns dict or None.
    """
    json_name = f"{graph_key}_{algo}_{timestamp_str}.json"
    json_path = json_dir / json_name
    if json_path.exists():
        with open(json_path) as f:
            return _json.load(f)
    return None


# ============================================================================
# GROUPING
# ============================================================================

def discover_groups(input_dir: Path, target_algos: list[str]):
    """
    Scan directory for .mp4 files, group by graph_key.

    Returns:
        complete  — groups with ALL target algos present
        all_videos — every group (for incomplete warnings)

    Each entry stores (datetime, timestamp_str, path) so we can
    locate the matching JSON sidecar later.
    """
    # graph_key -> algo -> (datetime, timestamp_str, path)
    best = defaultdict(dict)
    duplicates_skipped = 0

    for mp4 in input_dir.glob("*.mp4"):
        graph_key, algo, dt, ts_str = parse_video_filename(mp4.name)
        if not graph_key:
            continue

        if algo in best[graph_key]:
            existing_dt, _, existing_path = best[graph_key][algo]
            if dt > existing_dt:
                print(f"  ♻️  {graph_key}/{algo}: keeping {mp4.name} "
                      f"(replacing older {existing_path.name})")
                best[graph_key][algo] = (dt, ts_str, mp4)
            else:
                print(f"  ♻️  {graph_key}/{algo}: skipping {mp4.name} "
                      f"(keeping newer {existing_path.name})")
            duplicates_skipped += 1
        else:
            best[graph_key][algo] = (dt, ts_str, mp4)

    if duplicates_skipped:
        print(f"\n  Resolved {duplicates_skipped} duplicate(s) by timestamp.\n")

    # Build convenient lookups
    all_videos = {}
    all_timestamps = {}
    for gk, algos in best.items():
        all_videos[gk] = {algo: path for algo, (dt, ts, path) in algos.items()}
        all_timestamps[gk] = {algo: ts for algo, (dt, ts, path) in algos.items()}

    target_set = set(target_algos)
    complete = {
        gk: algos
        for gk, algos in all_videos.items()
        if target_set.issubset(algos.keys())
    }

    return complete, all_videos, all_timestamps


# ============================================================================
# VIDEO DURATION QUERY
# ============================================================================

ALGO_TIEBREAK = {name: i for i, name in enumerate(DEFAULT_ALGOS)}


def get_duration(video_path: Path) -> float:
    """Get video duration in seconds via ffprobe. Returns 0.0 on failure."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        info = _json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def order_by_duration(algo_dict: dict[str, Path],
                      target_algos: list[str]) -> list[tuple[str, Path, float]]:
    """
    Return (algo_name, path, duration) triples sorted longest-first.
    Ties broken by DEFAULT_ALGOS order (Greedy → DSATUR → SmlLst).
    """
    durations = {
        algo: get_duration(path)
        for algo, path in algo_dict.items()
        if algo in target_algos
    }
    return sorted(
        [(a, algo_dict[a], durations.get(a, 0.0)) for a in target_algos],
        key=lambda t: (-t[2], ALGO_TIEBREAK.get(t[0], 99)),
    )


# ============================================================================
# METADATA BUILDER
# ============================================================================

def build_combined_metadata(graph_key: str, ordered: list, json_dir: Path,
                            all_timestamps: dict):
    """
    Build a rich metadata dict for the combined 3-pack video.
    Pulls from per-run JSON files where available, falls back to
    video-duration-only data otherwise.

    Returns dict ready to be written as JSON sidecar.
    """
    algo_details = {}
    # Use the first algo's JSON to get graph-level stats
    graph_meta = {}

    for algo, path, duration in ordered:
        ts_str = all_timestamps.get(graph_key, {}).get(algo)
        run_json = load_run_json(json_dir, graph_key, algo, ts_str) if ts_str else None

        detail = {
            "algo":             algo,
            "video_file":       path.name,
            "video_duration_s": round(duration, 2),
        }

        if run_json:
            detail["algo_time_ms"]  = run_json.get("algo_time_ms")
            detail["assignments"]   = run_json.get("assignments")
            detail["backtracks"]    = run_json.get("backtracks")
            detail["conflicts"]     = run_json.get("conflicts")
            detail["colors_used"]   = run_json.get("colors_used")
            detail["seed"]          = run_json.get("seed")
            detail["dsatur_fallback"] = run_json.get("dsatur_fallback", False)

            # Grab graph-level data from first available JSON
            if not graph_meta:
                graph_meta = {
                    "graph_name":  run_json.get("graph_name", graph_key),
                    "module":      run_json.get("module", "unknown"),
                    "source":      run_json.get("source", ""),
                    "n":           run_json.get("n"),       # vertices
                    "m":           run_json.get("m"),       # edges
                    "faces":       run_json.get("faces"),   # F = E - V + 2
                    "maxdeg":      run_json.get("maxdeg"),
                    "avgdeg":      run_json.get("avgdeg"),
                    "euler_ok":    run_json.get("euler_ok"),
                    "comps":       run_json.get("comps"),
                }

        algo_details[algo] = detail

    # Compute cross-algorithm summary stats
    durations = [d["video_duration_s"] for d in algo_details.values()]
    algo_times = [d.get("algo_time_ms") for d in algo_details.values()
                  if d.get("algo_time_ms") is not None]

    fastest_dur = min(durations) if durations else 0
    slowest_dur = max(durations) if durations else 0
    time_gap_s  = round(slowest_dur - fastest_dur, 2)

    fastest_algo_ms = min(algo_times) if algo_times else None
    slowest_algo_ms = max(algo_times) if algo_times else None
    algo_time_gap_ms = round(slowest_algo_ms - fastest_algo_ms, 2) if (
        fastest_algo_ms is not None and slowest_algo_ms is not None) else None

    # Determine which algo was fastest/slowest by algorithm compute time
    if algo_times:
        sorted_by_compute = sorted(
            [(a, d.get("algo_time_ms", float("inf"))) for a, d in algo_details.items()],
            key=lambda x: x[1])
        fastest_algo = sorted_by_compute[0][0]
        slowest_algo = sorted_by_compute[-1][0]
    else:
        fastest_algo = None
        slowest_algo = None

    # Total backtracks across all algos
    total_backtracks = sum(d.get("backtracks", 0) for d in algo_details.values())
    any_fallback = any(d.get("dsatur_fallback", False) for d in algo_details.values())

    # Density = 2m / (n*(n-1)) for simple graphs
    n = graph_meta.get("n", 0)
    m = graph_meta.get("m", 0)
    density = round(2 * m / (n * (n - 1)), 4) if n and n > 1 else None

    # Edge-to-vertex ratio
    ev_ratio = round(m / n, 2) if n else None

    meta = {
        "graph_key":            graph_key,
        **graph_meta,
        "density":              density,
        "edge_vertex_ratio":    ev_ratio,
        "algo_order_lr":        [a for a, _, _ in ordered],
        "algorithms":           algo_details,
        "video_duration_min_s": round(fastest_dur, 2),
        "video_duration_max_s": round(slowest_dur, 2),
        "video_time_gap_s":     time_gap_s,
        "algo_time_fastest_ms": fastest_algo_ms,
        "algo_time_slowest_ms": slowest_algo_ms,
        "algo_time_gap_ms":     algo_time_gap_ms,
        "fastest_algo":         fastest_algo,
        "slowest_algo":         slowest_algo,
        "total_backtracks":     total_backtracks,
        "dsatur_needed_fallback": any_fallback,
        "combined_datetime":    datetime.now().strftime("%Y%m%dT%H%M%S"),
    }

    return meta


# ============================================================================
# FFMPEG COMBINE
# ============================================================================

def combine_side_by_side(video_paths: list[Path], output_path: Path):
    """
    Use FFmpeg to place N videos side-by-side horizontally.
    All inputs scaled to the same height before stacking.
    """
    n = len(video_paths)

    input_args = []
    for vp in video_paths:
        input_args += ["-i", str(vp)]

    TARGET_HEIGHT = 720
    filter_parts = []
    stack_inputs = []

    for i in range(n):
        label = f"v{i}"
        filter_parts.append(
            f"[{i}:v]scale=-2:{TARGET_HEIGHT},setsar=1[{label}]"
        )
        stack_inputs.append(f"[{label}]")

    stack_str = "".join(stack_inputs)
    filter_parts.append(f"{stack_str}hstack=inputs={n}[out]")
    filter_graph = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-an",
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "medium",
        str(output_path),
    ]

    print(f"  Running: {' '.join(cmd[:6])} ... → {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ FFmpeg error:\n{result.stderr[-500:]}")
        return False

    print(f"  ✅ Created: {output_path}")
    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Combine algorithm videos side-by-side per graph."
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Actually render. Without this flag, just previews groups."
    )
    parser.add_argument(
        "--algos", nargs="+", default=DEFAULT_ALGOS,
        help=f"Algorithms to include, in L→R order (default: {DEFAULT_ALGOS})"
    )
    parser.add_argument(
        "--input-dir", default=VIDEO_INPUT_DIR,
        help="Override input video directory."
    )
    parser.add_argument(
        "--json-dir", default=JSON_INPUT_DIR,
        help="Override JSON metadata directory."
    )
    parser.add_argument(
        "--output-dir", default=COMBINED_OUTPUT_DIR,
        help="Override output directory for combined videos."
    )
    args = parser.parse_args()

    input_dir  = Path(args.input_dir)
    json_dir   = Path(args.json_dir)
    output_dir = Path(args.output_dir)
    target_algos = args.algos

    if not input_dir.is_dir():
        print(f"❌ Input directory not found: {input_dir}")
        return

    complete, all_videos, all_timestamps = discover_groups(input_dir, target_algos)

    # --- Summary ---
    algo_str = " | ".join(target_algos)
    print(f"\n{'='*70}")
    print(f"  Video Combiner  —  [{algo_str}]")
    print(f"{'='*70}")
    print(f"  Input:    {input_dir}")
    print(f"  JSON:     {json_dir}")
    print(f"  Output:   {output_dir}")
    print(f"  Total .mp4 files found:    {sum(len(a) for a in all_videos.values())}")
    print(f"  Unique graphs found:       {len(all_videos)}")
    print(f"  Complete groups (all {len(target_algos)} algos): {len(complete)}")
    print()

    # --- Warn about incomplete groups ---
    incomplete = {
        gk: algos for gk, algos in all_videos.items()
        if gk not in complete
    }
    if incomplete:
        print(f"  ⚠️  {len(incomplete)} graph(s) could NOT be combined (missing algos):")
        for gk in sorted(incomplete.keys()):
            present = sorted(incomplete[gk].keys())
            missing = sorted(set(target_algos) - set(present))
            print(f"     {gk:40s}  has: {', '.join(present):30s}  "
                  f"MISSING: {', '.join(missing)}")
        print()

    if not complete:
        print("  No complete groups to process.")
        return

    # --- Preview or render ---
    for gk in sorted(complete.keys()):
        algos = complete[gk]
        ordered = order_by_duration(algos, target_algos)

        print(f"  📊 {gk}")
        for algo, path, dur in ordered:
            print(f"       {algo:10s} ({dur:6.1f}s) → {path.name}")

        if args.run:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build metadata
            meta = build_combined_metadata(gk, ordered, json_dir, all_timestamps)

            # Filename with datetime stamp
            dt_stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            ordered_names = [a for a, _, _ in ordered]
            out_name = f"{gk}_combined_{'_'.join(ordered_names)}_{dt_stamp}.mp4"
            out_path = output_dir / out_name

            success = combine_side_by_side([p for _, p, _ in ordered], out_path)

            if success:
                # Write sidecar JSON
                meta["combined_video_file"] = out_name
                json_out = out_path.with_suffix(".json")
                with open(json_out, "w") as f:
                    _json.dump(meta, f, indent=2)
                print(f"  📋 Metadata → {json_out.name}")

        print()

    if not args.run:
        print(f"  ℹ️  Dry run — add --run to actually render "
              f"{len(complete)} combined videos.")


if __name__ == "__main__":
    main()