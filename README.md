# pubmed-proto

Generates **`pubmed_proto`** — a typed Python package for parsing NLM PubMed XML into protobuf and pydantic models —
from the PubMed DTD.

This repository is the **generator**, not the package. It holds the inputs (`pubmed.dtd`, `pubmed_transforms.yaml`) and
drives [`xsd-former`](https://github.com/populationgenomics/xsd-former) (the `xsdformer` CLI) to emit the `pubmed_proto`
source tree, which is then built into a wheel and published to PyPI. The generated tree (`generated/`) and build outputs
(`dist/`) are gitignored — only the inputs are version-controlled.

## Consuming `pubmed_proto`

Depend on the published wheel, not this repo:

```
pip install pubmed_proto      # or: uv add pubmed_proto
```

```python
from lxml import etree
from pubmed_proto import xml_converter, pydantic_converter, models

tree = etree.parse("efetch_output.xml")
record_set = xml_converter.PubmedArticleSet(tree.getroot())  # XML -> protobuf

proto = record_set.pubmed_article[0]                          # or .pubmed_book_article
model = pydantic_converter.PubmedArticle_from_proto(proto)  # protobuf -> pydantic
json_str = model.model_dump_json()                          # pydantic -> JSON
```

An `efetch` response is a `PubmedArticleSet` of journal articles (`PubmedArticle`) and Bookshelf records
(`PubmedBookArticle` — a GeneReviews chapter, say); both are modelled, with one converter per message.

The package exposes four modules (all typed; ships `py.typed`):

| module               | purpose                                             |
| -------------------- | --------------------------------------------------- |
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

Shaping the output is done in **`pubmed_transforms.yaml`** — dropping admin types, flattening list wrappers, coercing
booleans/timestamps, and serializing rich-text fields to markdown. See the
[`xsd-former`](https://github.com/populationgenomics/xsd-former) docs for the transform reference.

## Provenance & attribution

`pubmed.dtd` is derived from the **U.S. National Library of Medicine PubMed DTD**, version `pubmed_250101` (dated
2024-08-28):

<https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd>

NLM DTDs are U.S. Government works and public domain in the United States; the MIT `LICENSE` in this repo covers CPG's
own files (transforms, generator wiring, tests), not the NLM DTD.

Courtesy of the U.S. National Library of Medicine. NLM does not endorse this package. The vendored DTD and the PubMed
records under `tests/records/` are pinned snapshots and do not necessarily reflect the most current data available from
NLM — fetch from NLM directly for current data. The records are `efetch` output included solely as parser fixtures. The
two journal records are verbatim; their abstracts remain the copyright of their publishers or authors. Of the two
Bookshelf records, `pmid_25834910.xml` (an NIH Molecular Libraries probe report) is verbatim: the collection's Copyright
and Permissions statement reads "This publication is in the public domain", and the record carries no copyright
statement. `pmid_20301425.xml` (a GeneReviews chapter) is trimmed: each `AbstractText` paragraph is replaced by a
placeholder sentence and `CopyrightInformation` is removed, so the fixture carries only bytes we may redistribute — the
gate exercises the record's structure, and its prose is not ours. Everything else in it is verbatim.

**Local modification:** the external MathML module include (`<!ENTITY % mathml-in-pubmed SYSTEM "mathml-in-pubmed.mod">`
and its reference) was removed so the DTD is self-contained for schema generation — MathML markup in titles/abstracts is
not modelled. With that one include removed, the file is byte-identical to upstream `pubmed_250101`.

**Inline markup in attribute-less text elements:** `Affiliation`, `PublisherName`, `Suffix` and `VolumeTitle` are
declared as text with inline markup (`b`, `i`, `sub`, `sup`, `u`) and nothing else — no attributes, no MathML
alternative (they are exactly the `%text;` elements of that shape not otherwise dropped; `CoiStatement` is the fifth and
is in `drop_types`). Two transforms in `pubmed_transforms.yaml` collapse them: `drop_types` removes the inline-markup
types (`B`, `I`, `Sub`, `Sup`, `U`), which leaves each element a bare text wrapper, and `inline_wrappers: true` then
folds it into its parent as a plain string. Both run before `serialize_content`, so an entry for these names has no
effect, and the converter keeps only the text before the first inline element
(`<PublisherName>Univ of <i>Washington</i></PublisherName>` parses as `Univ of `). Elements with attributes or a MathML
alternative stay messages and are the ones `serialize_content` renders to markdown.

The DTD is **vendored deliberately, not fetched at build time**: it's a modified derivative (so a fetch wouldn't
reproduce it), and pinning the exact bytes keeps the generated schema reproducible. The full provenance also lives in a
comment at the top of `pubmed.dtd`.

## Releasing

The published version is **`build.version` in `pubmed_transforms.yaml`** (what `xsdformer` stamps into the wheel). To
release:

1. Bump `build.version` in `pubmed_transforms.yaml`.
1. Publish a GitHub Release tagged `vX.Y.Z` matching that version.

The `release` workflow generates, builds, and publishes to PyPI via Trusted Publishing (OIDC). It fails if the tag and
`build.version` disagree.
