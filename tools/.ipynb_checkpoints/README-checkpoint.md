# Tools

Post-processing utilities for rendered videos and metadata.

## `combine_algorithm_videos.py`

Scans the rendered video output, groups videos by graph key, and stitches
matching algorithm videos (Greedy, DSATUR, Smallest-Last) side-by-side
into a single comparison MP4.  Writes a JSON sidecar with metadata.

```bash
# Preview which groups are ready
python tools/combine_algorithm_videos.py

# Actually render
python tools/combine_algorithm_videos.py --run

# Custom algorithm set
python tools/combine_algorithm_videos.py --run --algos Greedy DSATUR SmlLst Random
```

Requires `ffmpeg` and `ffprobe` on your PATH.