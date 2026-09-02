"""Round-trip gate over real PubMed records.

This is pubmed-proto's release safety net: it builds the package from *this
repo's* ``pubmed.dtd`` + ``pubmed_transforms.yaml`` using the shipping path
(the ``xsdformer`` CLI, exactly what ``make build`` runs), then checks that
real NLM PubMed XML records survive the full generated suite:

* ``XML -> proto -> pydantic -> proto`` is identical in the proto,
* ``proto -> pydantic -> JSON -> pydantic`` round-trips in pydantic, and
* the field the DTD requires of each kind is populated (``ArticleTitle``,
  ``BookTitle``), and the optional book fields the gate covers (``Sections``,
  ``DateRevised``) are in the proto exactly when they are in the XML — so a
  transform edit that drops a type fails here instead of shipping an emptier
  schema that still round-trips.

A DTD or transform edit that breaks the generated wheel fails here before it
can be published. Fixtures in ``records/`` are ``efetch`` output, verbatim
except ``pmid_20301425.xml``, whose ``AbstractText`` paragraphs are a
placeholder and whose ``CopyrightInformation`` is removed (see the README's
provenance section). Each is a ``PubmedArticleSet`` holding journal articles
(``PubmedArticle``) and/or Bookshelf records (``PubmedBookArticle``), and every
member is checked.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).parents[1]
_RECORDS_DIR = pathlib.Path(__file__).parent / 'records'
_RECORDS = sorted(_RECORDS_DIR.glob('*.xml'))

# Body of the per-record subprocess; formatted with the import root and the
# record path.
_ROUNDTRIP_SCRIPT = """
import sys
sys.path.insert(0, {built_package!r})
from lxml import etree
from pubmed_proto import xml_converter, pydantic_converter, models


def roundtrip(proto, from_proto, to_proto, model_cls):
    # XML -> proto -> pydantic -> proto is identical in the proto.
    model = from_proto(proto)
    assert to_proto(model) == proto, type(proto).__name__

    # proto -> pydantic -> JSON -> pydantic round-trips in pydantic.
    restored = model_cls.model_validate_json(model.model_dump_json())
    assert restored == model, type(proto).__name__


def check_article_populated(proto):
    assert proto.medline_citation.article.article_title.value, 'ArticleTitle not populated'


def check_book_populated(proto, book_document_el):
    document = proto.book_document
    assert document.book.book_title.value, 'BookTitle not populated'
    # Optional in the DTD, so presence is compared with the XML rather than asserted.
    has_sections = book_document_el.find('Sections') is not None
    assert bool(document.sections) == has_sections, 'Sections presence differs from the XML'
    has_date_revised = book_document_el.find('DateRevised') is not None
    assert document.HasField('date_revised') == has_date_revised, 'DateRevised presence differs from the XML'


root = etree.parse({record!r}).getroot()
record_set = xml_converter.PubmedArticleSet(root)
assert record_set.pubmed_article or record_set.pubmed_book_article, 'empty PubmedArticleSet'
book_document_els = root.findall('PubmedBookArticle/BookDocument')

for proto in record_set.pubmed_article:
    check_article_populated(proto)
    roundtrip(
        proto,
        pydantic_converter.PubmedArticle_from_proto,
        pydantic_converter.PubmedArticle_to_proto,
        models.PubmedArticle,
    )
for proto, book_document_el in zip(record_set.pubmed_book_article, book_document_els, strict=True):
    check_book_populated(proto, book_document_el)
    roundtrip(
        proto,
        pydantic_converter.PubmedBookArticle_from_proto,
        pydantic_converter.PubmedBookArticle_to_proto,
        models.PubmedBookArticle,
    )
"""


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
    script = _ROUNDTRIP_SCRIPT.format(built_package=str(built_package), record=str(record))
    result = subprocess.run(
        [sys.executable, '-c', script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
