# Multimodal-Data-Forge

> **Quality-aware distributed multimodal data curation, auto-annotation, and serving pipeline for image-text datasets.**

Multimodal-Data-Forge is an engineering-oriented pipeline for preparing image-text data for multimodal model training. It combines configurable quality filtering, CLIP-based alignment, semantic deduplication, quality-aware representative selection, Ray-based parallel execution, BLIP auto-annotation, and a lightweight Ray Serve inference API.

The project is evaluated on a **1,000-sample Visual Genome subset** and includes reproducible benchmarks and tests.

![Multimodal-Data-Forge Architecture](assets/architecture.png)

---

## Highlights

| Capability | Implementation |
| --- | --- |
| Real multimodal data | Visual Genome image-text subset |
| Unified ingestion | `VisualGenomeAdapter` -> `MultimodalSample` |
| Quality filtering | Resolution, blur, and CLIP alignment filters |
| Distributed execution | Local executor and Ray `ActorPool` executor |
| Semantic deduplication | CLIP embeddings + cosine similarity |
| Quality-aware selection | Resolution + sharpness + alignment score |
| Auto-annotation | BLIP image captioning with batch inference |
| Online serving | Ray Serve HTTP endpoint |
| Validation | 6 pytest tests, including Local/Ray consistency |
| Benchmarking | 100 / 500 / 1,000-sample scaling experiments |

---

## Pipeline

```text
Visual Genome
      |
      v
VisualGenomeAdapter
      |
      v
MultimodalSample
      |
      v
Validator -> Image Loader -> Resolution Filter -> Blur Filter -> CLIP Alignment
      |
      v
Local / Ray Executor
      |
      v
Semantic Deduplication
      |
      v
Quality-Aware Selection
      |
      v
Curated Dataset
      |
      v
BLIP Auto-Annotation

Online path: VLMAnnotator -> Ray Serve -> HTTP API
```

Sample-level operators can run in parallel, while semantic deduplication runs after merging because it requires a global dataset view.

---

## Quality Curation

| Stage | Purpose | Main Signal |
| --- | --- | --- |
| Validator | Reject malformed samples | Required fields |
| Image Loader | Verify and decode images | File validity |
| Resolution Filter | Remove undersized images | Width / height |
| Blur Filter | Remove low-sharpness images | Laplacian variance |
| CLIP Alignment | Remove weak image-text pairs | CLIP similarity |
| Semantic Dedup | Detect near-duplicate samples | CLIP embedding similarity |
| Quality Selection | Keep the better duplicate representative | Composite quality score |

Operators and thresholds are configured in `config/pipeline.yaml`.

### Quality-aware duplicate selection

```text
quality =
    0.2 * resolution_score
  + 0.3 * sharpness_score
  + 0.5 * alignment_score
```

```text
resolution_score = min(width * height / (1920 * 1080), 1)
sharpness_score  = min(blur_score / 500, 1)
alignment_score  = clip_score clipped to [0, 1]
```

This is an engineering heuristic for representative selection, not a learned quality model.

---

## Data Curation Results

Evaluation dataset: **1,000 Visual Genome image-text samples**.

| Stage | Remaining | Removed |
| --- | ---: | ---: |
| Input | 1,000 | - |
| Resolution Filter | 809 | 191 |
| Blur Filter | 775 | 34 |
| CLIP Alignment | 671 | 104 |
| Semantic Deduplication | **664** | 7 |

Final result: **664 curated samples** and **336 filtered or deduplicated samples**.

---

## Distributed Execution

The same quality pipeline supports `LocalExecutor` and `RayExecutor`. `RayExecutor` uses persistent Ray actors and `ActorPool` for batch-level parallel processing.

### Scaling Benchmark

Each configuration was executed **3 times**; the median is reported.

| Samples | Executor | Median Time (s) | Throughput (samples/s) | Accepted | Rejected |
| ---: | --- | ---: | ---: | ---: | ---: |
| 100 | Local | 17.33 | 5.77 | 60 | 40 |
| 100 | Ray-2W | 17.65 | 5.67 | 60 | 40 |
| 100 | Ray-4W | 14.17 | 7.06 | 60 | 40 |
| 500 | Local | 105.74 | 4.73 | 329 | 171 |
| 500 | Ray-2W | 91.16 | 5.48 | 329 | 171 |
| 500 | Ray-4W | 64.19 | 7.79 | 329 | 171 |
| 1,000 | Local | 217.42 | 4.60 | 671 | 329 |
| 1,000 | Ray-2W | 180.03 | 5.55 | 671 | 329 |
| 1,000 | Ray-4W | 124.33 | **8.04** | 671 | 329 |

At 1,000 samples, Ray-4W increased throughput from **4.60 to 8.04 samples/s (1.75x)** and reduced execution time from **217.42 s to 124.33 s**, while preserving the same accepted/rejected results.

![Scaling Benchmark](assets/scaling_benchmark.png)

The benchmark reflects the tested single-machine workload; it does not claim linear or multi-node scaling.

---

## VLM Auto-Annotation

Curated samples can optionally be passed to BLIP caption generation.

```text
Curated Samples -> VLMAnnotator -> BLIP Batch Inference -> annotations.jsonl
```

Model:

```text
Salesforce/blip-image-captioning-base
```

Example:

```json
{
  "sample_id": "vg_000001",
  "image_path": "data/visual_genome/images/vg_000001.jpg",
  "caption": "a tree with no leaves",
  "model_name": "Salesforce/blip-image-captioning-base",
  "status": "success",
  "error": null
}
```

The annotation stage is configurable through YAML and supports batch inference.

---

## Ray Serve API

The same `VLMAnnotator` is reused by a lightweight Ray Serve deployment.

Start:

```bash
serve run src.serving.vlm_service:app
```

Endpoint:

```text
POST http://127.0.0.1:8000/
```

Request:

```json
{
  "sample_id": "test_001",
  "image_path": "data/visual_genome/images/vg_000001.jpg"
}
```

Response:

```json
{
  "sample_id": "test_001",
  "image_path": "data/visual_genome/images/vg_000001.jpg",
  "caption": "a tree with no leaves",
  "model_name": "Salesforce/blip-image-captioning-base",
  "status": "success",
  "error": null
}
```

This is a local proof-of-concept service using server-accessible image paths, not a production upload API.

---

## Configuration

```yaml
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

---

## Project Structure

```text
Multimodal-Data-Forge/
|-- assets/
|   |-- architecture.png
|   `-- scaling_benchmark.png
|-- benchmarks/
|   |-- benchmark_cold_steady.py
|   |-- benchmark_executor.py
|   |-- plot_scaling_benchmark.py
|   `-- scaling_results.csv
|-- config/
|   `-- pipeline.yaml
|-- data/
|   `-- visual_genome/
|       `-- samples.jsonl
|-- scripts/
|   |-- batch_annotate.py
|   |-- download_visual_genome_subset.py
|   `-- test_visual_genome_adapter.py
|-- src/
|   |-- adapters/
|   |-- annotation/
|   |-- executors/
|   |-- operators/
|   |-- schema/
|   |-- serving/
|   |-- config_loader.py
|   |-- operator_factory.py
|   `-- pipeline.py
|-- tests/
|   |-- test_executor_consistency.py
|   |-- test_quality_filters.py
|   |-- test_semantic_dedup.py
|   `-- test_validator.py
|-- .gitignore
|-- main.py
|-- requirements.txt
`-- README.md
```

Downloaded Visual Genome images and generated outputs are excluded from version control.

---

## Quick Start

```bash
git clone https://github.com/Ellen112-gif/Multimodal-Data-Forge.git
cd Multimodal-Data-Forge
pip install -r requirements.txt
```

Prepare the Visual Genome subset:

```bash
python scripts/download_visual_genome_subset.py
```

Run:

```bash
python main.py
```

Typical outputs:

```text
outputs/dataset.jsonl
outputs/metrics.json
outputs/annotations.jsonl
```

The first CLIP or BLIP run may download pretrained model weights.

---

## Reproduce Benchmarks

Formal scaling benchmark:

```bash
python benchmarks/benchmark_executor.py
```

Cold-start vs. steady-state benchmark:

```bash
python benchmarks/benchmark_cold_steady.py
```

Results:

```text
benchmarks/scaling_results.csv
```

---

## Tests

```bash
python -m pytest tests -v
```

Current result:

```text
6 passed
```

Tests cover Local/Ray result consistency, resolution filtering, quality-aware scoring, validation, and missing image-path rejection.

---

## Tech Stack

| Area | Technologies |
| --- | --- |
| Language | Python |
| Distributed Processing | Ray, ActorPool |
| Model Serving | Ray Serve |
| Image Processing | OpenCV, Pillow |
| Multimodal Embeddings | CLIP |
| Auto-Annotation | BLIP, Transformers |
| Deep Learning | PyTorch |
| Configuration | YAML |
| Testing | pytest |

---

## Scope and Limitations

**Current scope**

- single-machine Local/Ray execution
- Visual Genome image-text ingestion
- CLIP-based filtering and semantic deduplication
- full pairwise similarity for the current dataset size
- heuristic quality-aware representative selection
- BLIP caption generation
- local Ray Serve inference

**Not currently implemented**

- multi-node cluster deployment
- ANN/vector-database deduplication at very large scale
- video, audio, robot trajectory, action/state, or ROS data
- learned multimodal quality scoring
- production authentication, object storage, or upload APIs

These boundaries keep the benchmark and functionality claims aligned with the implemented system.

---

## Summary

```text
Real Data
   -> Validation
   -> Quality Filtering
   -> Distributed Processing
   -> Semantic Deduplication
   -> Quality-Aware Selection
   -> VLM Auto-Annotation
   -> Lightweight Online Serving
```

Multimodal-Data-Forge focuses on **data quality, reproducible engineering, distributed execution, and model-ready dataset preparation** rather than training a new multimodal model.
