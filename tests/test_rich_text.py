r"""Rich-text fields escape literal markdown marker characters.

PubMed text carries literal asterisks and underscores in HGVS notation
(``p.Arg123*``, ``fs*27``, ``c.2568_2569del``). The fields in
``serialize_content`` render inline markup as markdown markers, so the
converter backslash-escapes those characters in text: ``\``, ``*``, ``_``,
``^`` and ``~`` everywhere, and ``)`` inside ``^(...)`` and ``~(...)``. These
tests run the built converter on the shapes found in live records and check
both the serialized value and that ``xml_converter.markdown_to_plain_text``
inverts it to the element's text content.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest
from lxml import etree

# Case id -> (converter, XML, expected serialized value). The pmid_* cases are from live records.
_CASES = {
    'pmid_34207366_title': (
        'ArticleTitle',
        '<ArticleTitle><i>Cis</i>-Segregation of c.1171C&gt;T Stop Codon (p.R391*) in <i>SERPINC1</i> Gene and'
        ' c.1691G&gt;A Transition (p.R506Q) in <i>F5</i> Gene and Selected GWAS Multilocus Approach in Inherited'
        ' Thrombophilia.</ArticleTitle>',
        r'*Cis*-Segregation of c.1171C>T Stop Codon (p.R391\*) in *SERPINC1* Gene and c.1691G>A Transition (p.R506Q)'
        r' in *F5* Gene and Selected GWAS Multilocus Approach in Inherited Thrombophilia.',
    ),
    'pmid_26586665_abstract': (
        'AbstractText',
        '<AbstractText Label="BACKGROUND" NlmCategory="BACKGROUND">The K3326X variant in BRCA2'
        ' (BRCA2*c.9976A&gt;T; p.Lys3326*; rs11571833)</AbstractText>',
        r'The K3326X variant in BRCA2 (BRCA2\*c.9976A>T; p.Lys3326\*; rs11571833)',
    ),
    'pmid_39705914_abstract': (
        'AbstractText',
        '<AbstractText Label="RESULTS" NlmCategory="RESULTS">a novel homozygous nonsense mutation'
        ' (c.2568_2569del p.Gly857Alafs*27)</AbstractText>',
        r'a novel homozygous nonsense mutation (c.2568\_2569del p.Gly857Alafs\*27)',
    ),
    'superscript_beside_caret': (
        'AbstractText',
        '<AbstractText>Ca<sup>2+</sup> influx in 10^3 cells, Pax6<sup>(+/-)</sup> mice (n = 4)</AbstractText>',
        r'Ca^(2+) influx in 10\^3 cells, Pax6^((+/-\)) mice (n = 4)',
    ),
    'literal_backslash_tilde_asterisk': (
        'ArticleTitle',
        '<ArticleTitle>Paths like C:\\data\\<i>raw</i> and ~50 *starred* items</ArticleTitle>',
        r'Paths like C:\\data\\*raw* and \~50 \*starred\* items',
    ),
}

_CONVERT_SCRIPT = """
import json
import sys
sys.path.insert(0, {built_package!r})
from lxml import etree
from pubmed_proto import xml_converter

cases = json.load(sys.stdin)
values = {{case: getattr(xml_converter, name)(etree.fromstring(xml)).value for case, (name, xml) in cases.items()}}
plain = {{case: xml_converter.markdown_to_plain_text(value) for case, value in values.items()}}
json.dump({{'values': values, 'plain': plain}}, sys.stdout)
"""


@pytest.fixture(scope='module')
def converted(built_package: pathlib.Path) -> dict[str, dict[str, str]]:
    """Run every case through the built converter in one subprocess (see test_roundtrip.py)."""
    result = subprocess.run(
        [sys.executable, '-c', _CONVERT_SCRIPT.format(built_package=str(built_package))],
        input=json.dumps({case: [name, xml] for case, (name, xml, _) in _CASES.items()}),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('case', _CASES)
def test_literal_marker_characters_are_escaped(case: str, converted: dict[str, dict[str, str]]) -> None:
    assert converted['values'][case] == _CASES[case][2]


@pytest.mark.parametrize('case', _CASES)
def test_markdown_to_plain_text_recovers_the_text_content(case: str, converted: dict[str, dict[str, str]]) -> None:
    element = etree.fromstring(_CASES[case][1])
    assert converted['plain'][case] == ''.join(map(str, element.itertext()))
