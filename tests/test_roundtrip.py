"""Round-trip gate over real PubMed records.

This is pubmed-proto's release safety net: it builds the package from *this
repo's* ``pubmed.dtd`` + ``pubmed_transforms.yaml`` using the shipping path
(the ``xsdformer`` CLI, exactly what ``make build`` runs), then checks that
real NLM PubMed XML records survive the full generated suite:

* ``XML -> proto -> pydantic -> proto`` is identical in the proto, and
* ``proto -> pydantic -> JSON -> pydantic`` round-trips in pydantic.

A DTD or transform edit that breaks the generated wheel fails here before it
can be published. Fixtures in ``records/`` are real ``efetch`` output.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).parents[1]
_RECORDS_DIR = pathlib.Path(__file__).parent / 'records'
_RECORDS = sorted(_RECORDS_DIR.glob('*.xml'))


@pytest.fixture(scope='module')
def built_package(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Generate the package once via the xsdformer CLI; return the import root."""
    out_dir = tmp_path_factory.mktemp('pubmed_build')
    subprocess.run(
        [
            'xsdformer',
            'build',
            str(_REPO_ROOT / 'pubmed.dtd'),
            '--transforms',
            str(_REPO_ROOT / 'pubmed_transforms.yaml'),
            '--out-dir',
            str(out_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out_dir


def test_records_present() -> None:
    assert _RECORDS, f'no PubMed record fixtures found in {_RECORDS_DIR}'


@pytest.mark.parametrize('record', _RECORDS, ids=lambda p: p.stem)
def test_pubmed_record_roundtrip(record: pathlib.Path, built_package: pathlib.Path) -> None:
    # Run in a subprocess so the dynamically compiled `*_pb2` (a global
    # descriptor-pool registration) stays isolated from the test process.
    script = f"""
import sys
sys.path.insert(0, {str(built_package)!r})
from lxml import etree
from pubmed_proto import xml_converter, pydantic_converter, models

tree = etree.parse({str(record)!r})
article_el = tree.getroot().find("PubmedArticle")
assert article_el is not None
proto = xml_converter.PubmedArticle(article_el)

# XML -> proto -> pydantic -> proto is identical in the proto.
model = pydantic_converter.PubmedArticle_from_proto(proto)
assert pydantic_converter.PubmedArticle_to_proto(model) == proto

# proto -> pydantic -> JSON -> pydantic round-trips in pydantic.
restored = models.PubmedArticle.model_validate_json(model.model_dump_json())
assert restored == model
"""
    result = subprocess.run(
        [sys.executable, '-c', script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
