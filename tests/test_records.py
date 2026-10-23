"""Record gate over real PubMed records.

This is pubmed-proto's release safety net: it builds the package from *this
repo's* ``pubmed.dtd`` + ``pubmed_transforms.yaml`` using the shipping path
(the ``xsdformer`` CLI, exactly what ``make build`` runs), then converts real
NLM PubMed XML records with the generated ``xml_converter`` and checks that:

* every journal article and Bookshelf record in the set comes out, each article
  under the PMID its XML carries,
* the field the DTD requires of each kind is populated (``ArticleTitle``,
  ``BookTitle``),
* every MeSH heading keeps its descriptor and qualifier names as in the XML,
  and
* the optional book fields the gate covers (``Sections``, ``DateRevised``) are
  in the proto exactly when they are in the XML,

so a transform edit that drops a type fails here instead of shipping an
emptier schema that still converts.

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
from lxml import etree

_RECORDS_DIR = pathlib.Path(__file__).parent / 'records'
_RECORDS = sorted(_RECORDS_DIR.glob('*.xml'))

# Body of the per-record subprocess; formatted with the import root and the
# record path.
_CONVERT_SCRIPT = """
import sys
sys.path.insert(0, {built_package!r})
from lxml import etree
from pubmed_proto import xml_converter


def check_article_populated(proto, article_el):
    citation = proto.medline_citation
    assert citation.pmid.value == article_el.findtext('MedlineCitation/PMID'), 'PMID differs from the XML'
    assert citation.article.article_title.value, 'ArticleTitle not populated'
    heading_els = article_el.findall('MedlineCitation/MeshHeadingList/MeshHeading')
    for heading, heading_el in zip(citation.mesh_heading_list, heading_els, strict=True):
        assert heading.descriptor_name.value == heading_el.findtext('DescriptorName'), 'DescriptorName differs'
        qualifier_names = [qualifier.value for qualifier in heading.qualifier_name]
        assert qualifier_names == [el.text for el in heading_el.findall('QualifierName')], 'QualifierName differs'


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
article_els = root.findall('PubmedArticle')
book_document_els = root.findall('PubmedBookArticle/BookDocument')

for proto, article_el in zip(record_set.pubmed_article, article_els, strict=True):
    check_article_populated(proto, article_el)
for proto, book_document_el in zip(record_set.pubmed_book_article, book_document_els, strict=True):
    check_book_populated(proto, book_document_el)
"""


def test_records_present() -> None:
    assert _RECORDS, f'no PubMed record fixtures found in {_RECORDS_DIR}'


def test_a_record_has_a_qualified_mesh_heading() -> None:
    # Without one, the MeSH name comparison in the record gate passes vacuously.
    assert any(etree.parse(record).find('.//MeshHeading/QualifierName') is not None for record in _RECORDS)


@pytest.mark.parametrize('record', _RECORDS, ids=lambda p: p.stem)
def test_pubmed_record_converts(record: pathlib.Path, built_package: pathlib.Path) -> None:
    # Run in a subprocess so the dynamically compiled `*_pb2` (a global
    # descriptor-pool registration) stays isolated from the test process.
    script = _CONVERT_SCRIPT.format(built_package=str(built_package), record=str(record))
    result = subprocess.run(
        [sys.executable, '-c', script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
