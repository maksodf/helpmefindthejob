<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# escolib — standalone ESCO/ISCO reconciliation

A small, **dependency-free** Python library that reconciles free text to
ESCO/ISCO occupation + skill concepts against a curated, CC-BY-4.0 dataset
(ISCO-08 / ESCO v1.1), with EN/DE label + colloquial-synonym (`altLabels`)
matching and dataset-version provenance.

It was extracted from the Helpmefindthejob civic-employment project so that
**any** civic-tech tool — housing, training-matching, benefits navigation —
can reuse occupation/skill reconciliation without depending on that
application. `escolib` imports only the Python standard library and **never
imports application code** (enforced by `tests/test_escolib_standalone.py`,
which runs it with the application package import-forbidden).

## Use it

Library:

```python
from escolib import EscoReconciler

reconciler = EscoReconciler()                 # loads the packaged dataset
result = reconciler.query("Krankenschwester", limit=1)
result.matches[0]["code"]                     # -> "2221.1"
result.datasetVersion                         # -> "v1-curated-2026-05-18"
```

Command line:

```console
$ python -m escolib "Krankenschwester" --limit 1
$ python -m escolib "frontend" --type occupation
$ python -m escolib "Deutsch B1" --type skill
```

Point it at your own dataset directory (same JSON shape) with `--data DIR`
or `EscoReconciler(base="path/to/esco")`.

## Reproducible benchmark

`python -m escolib.benchmark` measures synonym-resolution against the
committed dataset (no external ground truth needed):

| Metric | Result (v1-curated-2026-05-18) |
|---|---|
| Synonym + curated cases (all 7 persona families) | 20 |
| Recall (canonical code in matches) | **100%** |
| Top-1 (canonical code is first match) | **100%** |
| False positives on out-of-dataset queries | **0** / 6 |

The labelled set is derived from the dataset's own documented synonyms plus a
hand-curated cross-persona set; both are committed, so the number is fully
reproducible. `tests/test_escolib_standalone.py::EscolibBenchmark` pins it.

## Dataset + provenance

`escolib/data/esco/{occupations,skills}.json` is a persona-aligned curated
subset of ISCO-08 / ESCO v1.1 redistributed under **CC-BY-4.0** — see the
`attribution` / `license` / `sourceTaxonomies` headers in those files. Each
record carries the upstream `esco_uri` so consumers can verify provenance, and
`datasetVersion` pins the curated release. Codes are class-B authoritative
taxonomy; the `shortageDE2024` flag is a class-C national-shortage annotation.

When the data files are unavailable (e.g. a packaging step strips them), the
library falls back to a small embedded mini-dataset and reports
`datasetVersion: "v0-mini-fallback"` so callers can branch.

## Relationship to Helpmefindthejob

Helpmefindthejob's `query_esco_skill` MCP tool is a thin adapter over this
library (`company_discovery/mcp_tools.py`). The canonical dataset lives at the
repo's `reference/esco/`; `escolib/data/esco/` is a byte-identical packaged
copy for standalone users, and a drift-guard test keeps the two in sync.

## License

Code: Apache-2.0. Bundled dataset: CC-BY-4.0 (see the data files' attribution).
Reuse freely; please keep the attribution headers intact.
