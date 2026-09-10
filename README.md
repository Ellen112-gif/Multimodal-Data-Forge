# Multimodal-Data-Forge

> **Quality-aware distributed multimodal data curation, auto-annotation,
> and serving pipeline for image-text datasets.**

Multimodal-Data-Forge is an engineering-oriented pipeline for preparing
image-text data for multimodal model training. It combines configurable
quality filtering, CLIP-based alignment, semantic deduplication,
quality-aware representative selection, Ray-based parallel execution,
BLIP auto-annotation, and a lightweight Ray Serve inference API.

The project is evaluated on a **1,000-sample Visual Genome subset** and
includes reproducible benchmarks and tests.

```{=html}
<p align="center">
```
`<img src="assets/architecture.png" alt="Multimodal-Data-Forge architecture" width="900">`{=html}
```{=html}
</p>
```

------------------------------------------------------------------------

## Highlights

  Capability                Implementation
  ------------------------- -------------------------------------------------
  Real multimodal data      Visual Genome image-text subset
  Unified ingestion         `VisualGenomeAdapter` → `MultimodalSample`
  Quality filtering         Resolution, blur, and CLIP alignment filters
  Distributed execution     Local and Ray `ActorPool` executors
  Semantic deduplication    CLIP embeddings + cosine similarity
  Quality-aware selection   Resolution + sharpness + alignment score
  Auto-annotation           BLIP image captioning with true batch inference
  Online serving            Ray Serve HTTP endpoint
  Validation                6 pytest tests, including Local/Ray consistency
  Benchmarking              100 / 500 / 1,000-sample scaling experiments

------------------------------------------------------------------------

## Pipeline

``` text
Visual Genome
      │
      ▼
VisualGenomeAdapter
      │
      ▼
MultimodalSample
      │
      ▼
┌─────────────────────────────┐
│     Sample-Level Pipeline   │
│                             │
│  Validator                  │
│      ↓                      │
│  Image Loader               │
│      ↓                      │
│  Resolution Filter          │
│      ↓                      │
│  Blur Filter                │
│      ↓                      │
│  CLIP Alignment Filter      │
└──────────────┬──────────────┘
               │
        Local / Ray Executor
               │
               ▼
      Semantic Deduplication
               │
               ▼
      Quality-Aware Selection
               │
               ▼
        Curated Dataset
               │
               ▼
        BLIP Auto-Annotation

Separate online path:
VLMAnnotator → Ray Serve → HTTP API
```

The pipeline separates **sample-level operations**, which can run in
parallel, from **dataset-level semantic deduplication**, which requires
a global view of the accepted samples.

------------------------------------------------------------------------

## Quality Curation

Each image-text sample passes through a configurable operator chain.

  -----------------------------------------------------------------------
  Stage                   Purpose                 Main signal
  ----------------------- ----------------------- -----------------------
  Validator               Reject malformed        Required fields
                          samples                 

  Image Loader            Verify and decode       File validity
                          images                  

  Resolution Filter       Remove undersized       Width / height
                          images                  

  Blur Filter             Remove low-sharpness    Laplacian variance
                          images                  

  CLIP Alignment          Remove weak image-text  CLIP similarity
                          pairs                   

  Semantic Dedup          Detect near-duplicate   CLIP embedding
                          samples                 similarity

  Quality Selection       Keep the better         Composite quality score
                          duplicate               
                          representative          
  -----------------------------------------------------------------------

Operators are created from `config/pipeline.yaml`, making thresholds and
execution settings configurable without changing pipeline code.

### Quality-aware duplicate selection

When highly similar samples are found, the representative is selected
using a heuristic quality score:

``` text
quality =
    0.2 × resolution_score
  + 0.3 × sharpness_score
  + 0.5 × alignment_score
```

where:

``` text
resolution_score = min(width × height / (1920 × 1080), 1)

sharpness_score = min(blur_score / 500, 1)

alignment_score = clip_score clipped to [0, 1]
```

This score is an engineering heuristic used for representative
selection; it is not a learned quality model.

------------------------------------------------------------------------

## Visual Genome Results

The current evaluation uses **1,000 Visual Genome image-text samples**.

  Stage                      Remaining   Removed
  ------------------------ ----------- ---------
  Input                          1,000       ---
  Resolution filter                809       191
  Blur filter                      775        34
  CLIP alignment                   671       104
  Semantic deduplication           664         7

Final result:

``` text
1,000 input samples
      ↓
664 curated samples
336 rejected / deduplicated
```

The filtering stages therefore provide an auditable data-curation funnel
rather than only producing a final dataset.

------------------------------------------------------------------------

## Distributed Execution

The same operator pipeline can run through either:

``` text
LocalExecutor
```

or:

``` text
RayExecutor
```

`RayExecutor` uses persistent Ray actors and `ActorPool` for batch-level
parallel processing. Local and Ray execution share the same pipeline
logic.

### Scaling benchmark

Each configuration was run **3 times**, with the median reported.

  ----------------------------------------------------------------------------
       Samples Executor    Median Time    Throughput     Accepted     Rejected
                                   (s)   (samples/s)              
  ------------ ---------- ------------ ------------- ------------ ------------
           100 Local             17.33          5.77           60           40

           100 Ray-2W            17.65          5.67           60           40

           100 Ray-4W            14.17          7.06           60           40

           500 Local            105.74          4.73          329          171

           500 Ray-2W            91.16          5.48          329          171

           500 Ray-4W            64.19          7.79          329          171

         1,000 Local            217.42          4.60          671          329

         1,000 Ray-2W           180.03          5.55          671          329

         1,000 Ray-4W           124.33      **8.04**          671          329
  ----------------------------------------------------------------------------

At 1,000 samples, Ray with four workers increased throughput from **4.60
to 8.04 samples/s (1.75×)** and reduced execution time from **217.42 s
to 124.33 s**, while preserving the same accepted/rejected results.

```{=html}
<p align="center">
```
`<img src="assets/scaling_benchmark.png" alt="Scaling benchmark" width="760">`{=html}
```{=html}
</p>
```
The benchmark demonstrates useful parallel scaling on the tested
workload; it does **not** claim linear scaling or multi-node
performance.

------------------------------------------------------------------------

## VLM Auto-Annotation

Curated samples can optionally be passed to a BLIP captioning stage:

``` text
Curated Samples
      ↓
VLMAnnotator
      ↓
BLIP Batch Inference
      ↓
annotations.jsonl
```

Current model:

``` text
Salesforce/blip-image-captioning-base
```

Example output:

``` json
{
  "sample_id": "vg_000001",
  "image_path": "data/visual_genome/images/vg_000001.jpg",
  "caption": "a tree with no leaves",
  "model_name": "Salesforce/blip-image-captioning-base",
  "status": "success",
  "error": null
}
```

Annotation can be enabled or disabled in YAML and supports configurable
batch size and sample limits.

------------------------------------------------------------------------

## Ray Serve API

The same `VLMAnnotator` is reused by a lightweight Ray Serve deployment
for online inference.

Start the service:

``` powershell
serve run src.serving.vlm_service:app
```

The local endpoint is:

``` text
POST http://127.0.0.1:8000/
```

Example request body:

``` json
{
  "sample_id": "test_001",
  "image_path": "data/visual_genome/images/vg_000001.jpg"
}
```

Example response:

``` json
{
  "sample_id": "test_001",
  "image_path": "data/visual_genome/images/vg_000001.jpg",
  "caption": "a tree with no leaves",
  "model_name": "Salesforce/blip-image-captioning-base",
  "status": "success",
  "error": null
}
```

This is a local proof-of-concept serving path using server-accessible
image paths, not a production upload service.

------------------------------------------------------------------------

## Configuration

Core behavior is controlled through `config/pipeline.yaml`.

``` yaml
input:
  source: visual_genome
  path: "data/visual_genome/samples.jsonl"

output:
  dataset_path: "outputs/dataset.jsonl"
  metrics_path: "outputs/metrics.json"

executor:
  type: ray
  num_workers: 2
  batch_size: 2
  address: null

pipeline:
  operators:
    - name: validator
      enabled: true

    - name: image_loader
      enabled: true

    - name: resolution_filter
      enabled: true
      params:
        min_width: 512
        min_height: 512

    - name: blur_filter
      enabled: true
      params:
        threshold: 100.0

    - name: clip_alignment
      enabled: true
      params:
        threshold: 0.20

annotation:
  enabled: true
  model_name: "Salesforce/blip-image-captioning-base"
  batch_size: 4
  max_samples: 10
  output_path: "outputs/annotations.jsonl"
```

------------------------------------------------------------------------

## Project Structure

``` text
Multimodal-Data-Forge/
│
├── assets/
│   ├── architecture.png
│   └── scaling_benchmark.png
│
├── benchmarks/
│   ├── benchmark_cold_steady.py
│   ├── benchmark_executor.py
│   ├── plot_scaling_benchmark.py
│   └── scaling_results.csv
│
├── config/
│   └── pipeline.yaml
│
├── data/
│   └── visual_genome/
│       └── samples.jsonl
│
├── scripts/
│   ├── batch_annotate.py
│   ├── download_visual_genome_subset.py
│   └── test_visual_genome_adapter.py
│
├── src/
│   ├── adapters/
│   │   └── visual_genome_adapter.py
│   ├── annotation/
│   │   ├── annotation_schema.py
│   │   └── vlm_annotator.py
│   ├── executors/
│   │   ├── base_executor.py
│   │   ├── local_executor.py
│   │   └── ray_executor.py
│   ├── operators/
│   │   ├── base.py
│   │   ├── validator.py
│   │   ├── image_loader.py
│   │   ├── resolution_filter.py
│   │   ├── blur_filter.py
│   │   ├── clip_alignment.py
│   │   └── semantic_dedup.py
│   ├── schema/
│   │   └── multimodal_sample.py
│   ├── serving/
│   │   └── vlm_service.py
│   ├── config_loader.py
│   ├── operator_factory.py
│   └── pipeline.py
│
├── tests/
│   ├── test_executor_consistency.py
│   ├── test_quality_filters.py
│   ├── test_semantic_dedup.py
│   └── test_validator.py
│
├── .gitignore
├── main.py
├── requirements.txt
└── README.md
```

Generated outputs and downloaded Visual Genome images are intentionally
excluded from version control.

------------------------------------------------------------------------

## Installation

Python 3.9+ is recommended for the current project environment.

``` bash
git clone https://github.com/Ellen112-gif/Multimodal-Data-Forge.git
cd Multimodal-Data-Forge

pip install -r requirements.txt
```

The first CLIP or BLIP run may download pretrained model weights from
Hugging Face.

------------------------------------------------------------------------

## Prepare Visual Genome Data

Download the project subset:

``` bash
python scripts/download_visual_genome_subset.py
```

The script prepares:

``` text
data/visual_genome/images/
data/visual_genome/samples.jsonl
```

The raw Visual Genome archives and downloaded images are excluded from
Git.

------------------------------------------------------------------------

## Run the Pipeline

Run using the executor configured in YAML:

``` bash
python main.py
```

Typical outputs:

``` text
outputs/dataset.jsonl
outputs/metrics.json
outputs/annotations.jsonl
```

To switch execution mode, edit:

``` yaml
executor:
  type: local
```

or:

``` yaml
executor:
  type: ray
  num_workers: 4
```

------------------------------------------------------------------------

## Reproduce Benchmarks

Formal scaling benchmark:

``` bash
python benchmarks/benchmark_executor.py
```

Cold-start vs steady-state benchmark:

``` bash
python benchmarks/benchmark_cold_steady.py
```

Scaling results are saved to:

``` text
benchmarks/scaling_results.csv
```

------------------------------------------------------------------------

## Tests

Run:

``` bash
python -m pytest tests -v
```

Current result:

``` text
6 passed
```

The test suite covers:

-   Local/Ray executor result consistency
-   resolution acceptance and rejection
-   quality-aware representative scoring
-   valid sample validation
-   missing image-path rejection

------------------------------------------------------------------------

## Tech Stack

  Area                        Technologies
  --------------------------- --------------------
  Language                    Python
  Distributed processing      Ray, ActorPool
  Model serving               Ray Serve
  Vision / image processing   OpenCV, Pillow
  Multimodal embeddings       CLIP
  Auto-annotation             BLIP, Transformers
  Deep learning               PyTorch
  Configuration               YAML
  Testing                     pytest

------------------------------------------------------------------------

## Scope and Limitations

This repository is designed as a compact multimodal data-infrastructure
project rather than a production-scale platform.

Current scope:

-   single-machine Local/Ray execution
-   Visual Genome image-text ingestion
-   CLIP-based filtering and deduplication
-   full pairwise similarity for the current dataset size
-   heuristic quality-aware representative selection
-   BLIP caption generation
-   local Ray Serve inference

Not currently implemented:

-   multi-node cluster deployment
-   ANN/vector-database deduplication at very large scale
-   video, audio, robot trajectory, action/state, or ROS data
-   learned multimodal quality scoring
-   production authentication, object storage, or upload APIs

These boundaries are intentional so that benchmark and functionality
claims remain reproducible and aligned with the implemented system.

------------------------------------------------------------------------

## Summary

Multimodal-Data-Forge demonstrates an end-to-end multimodal data
engineering workflow:

``` text
Real Data
  → Validation
  → Quality Filtering
  → Distributed Processing
  → Semantic Deduplication
  → Quality-Aware Selection
  → VLM Auto-Annotation
  → Lightweight Online Serving
```

The project focuses on **data quality, reproducible engineering,
distributed execution, and model-ready dataset preparation** rather than
training a new multimodal model.
