"""Builds the package once per session, via the shipping path, for every test module."""

from __future__ import annotations

import pathlib
import subprocess

import pytest

_REPO_ROOT = pathlib.Path(__file__).parents[1]


@pytest.fixture(scope='session')
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
