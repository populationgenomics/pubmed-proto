# pubmed-proto

pubmed-proto owns *the shape of the `pubmed_proto` package*: which PubMed XML elements survive into the schema, how they
are named, and how they coerce. It does **not** own the generation engine (that is `xsd-former`) nor how consumers store
or render the parsed articles.

## Language

**Generator** (this repo): The inputs and build wiring that produce the package — `pubmed.dtd`,
`pubmed_transforms.yaml`, `Makefile`, `pyproject.toml`. Its own distribution is `pubmed-proto-generator`; it is never
published. *Avoid*: "the package" (that is the generated artifact, below).

**Generated package** (`pubmed_proto`): The published, consumable artifact — protobuf + pydantic models + converters,
emitted under `generated/` and built into a wheel. Gitignored; reproduced from the inputs on every build. *Avoid*:
"pubmed-proto" (that is the generator repo).

**Engine** (`xsd-former` / the `xsdformer` CLI): The external tool that turns a DTD + transform config into the
generated package. Constrained by a floor in `pyproject.toml` and pinned to an exact version in `uv.lock`; upgrading it
can change generated output, so it is treated as a build input.

**Transforms** (`pubmed_transforms.yaml`): The single source of truth for the schema's shape *and* its version
(`build.version`). Drops book/admin types, flattens list wrappers, coerces booleans/timestamps, serializes rich-text to
markdown.

## Invariants

- The generated tree and `dist/` are never committed — only inputs are.
- The published version is `build.version` in the transforms file, not the generator's own `pyproject.toml` version. The
  release tag must match it.
- `uv.lock` is committed: the artifact is only reproducible because the exact engine version is pinned there.
- The round-trip gate (`tests/`) builds from the real inputs and must pass before a release — it is what stops a
  DTD/transform edit shipping a broken wheel.
