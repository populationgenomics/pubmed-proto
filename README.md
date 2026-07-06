# pubmed-proto

Generates **`pubmed_proto`** — a typed Python package for parsing NLM PubMed XML
into protobuf and pydantic models — from the PubMed DTD.

This repository is the **generator**, not the package. It holds the inputs
(`pubmed.dtd`, `pubmed_transforms.yaml`) and drives
[`xsd-former`](https://github.com/populationgenomics/xsd-former) (the
`xsdformer` CLI) to emit the `pubmed_proto` source tree, which is then built into
a wheel and published to PyPI. The generated tree (`generated/`) and build
outputs (`dist/`) are gitignored — only the inputs are version-controlled.

## Consuming `pubmed_proto`

Depend on the published wheel, not this repo:

```
pip install pubmed_proto      # or: uv add pubmed_proto
```

```python
from lxml import etree
from pubmed_proto import xml_converter, pydantic_converter, models

tree = etree.parse("efetch_output.xml")
article_el = tree.getroot().find("PubmedArticle")

proto = xml_converter.PubmedArticle(article_el)     # XML  -> protobuf
model = pydantic_converter.PubmedArticle_from_proto(proto)  # protobuf -> pydantic
json_str = model.model_dump_json()                  # pydantic -> JSON
```

The package exposes four modules (all typed; ships `py.typed`):

| module               | purpose                                            |
| -------------------- | -------------------------------------------------- |
| `pubmed_pb2`         | compiled protobuf messages (`Article`, `Author`, …) |
| `models`             | pydantic models mirroring the protobuf schema       |
| `xml_converter`      | PubMed XML → protobuf (per-message factory funcs)   |
| `pydantic_converter` | protobuf ↔ pydantic (`X_from_proto` / `X_to_proto`) |

## Developing the generator

Requires [`uv`](https://docs.astral.sh/uv/).

```
make generate   # DTD + transforms -> generated/pubmed_proto/
make build      # generate, then build the wheel into dist/
make clean      # remove generated/ and dist/
uv run --group test pytest   # round-trip gate over real PubMed records
```

Shaping the output is done in **`pubmed_transforms.yaml`** — dropping
book/admin types, flattening list wrappers, coercing booleans/timestamps, and
serializing rich-text fields to markdown. See the
[`xsd-former`](https://github.com/populationgenomics/xsd-former) docs for the
transform reference.

## Releasing

The published version is **`build.version` in `pubmed_transforms.yaml`** (what
`xsdformer` stamps into the wheel). To release:

1. Bump `build.version` in `pubmed_transforms.yaml`.
2. Publish a GitHub Release tagged `vX.Y.Z` matching that version.

The `release` workflow generates, builds, and publishes to PyPI via Trusted
Publishing (OIDC). It fails if the tag and `build.version` disagree.
