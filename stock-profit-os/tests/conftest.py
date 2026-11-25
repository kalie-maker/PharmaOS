from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from engine.config import Mapping, Thresholds, load_mapping, load_thresholds
from engine.mock.generate import MockConfig, MockData, generate


@pytest.fixture(scope="session")
def thresholds() -> Thresholds:
    return load_thresholds()


@pytest.fixture(scope="session")
def farmatic() -> Mapping:
    return load_mapping("farmatic")


@pytest.fixture(scope="session")
def nixfarma() -> Mapping:
    return load_mapping("nixfarma")


@pytest.fixture(scope="session")
def small_mock() -> MockData:
    return generate(MockConfig(n_refs=300, seed=7))


@pytest.fixture(scope="session")
def small_mock_paths(small_mock: MockData, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return small_mock.write(tmp_path_factory.mktemp("mock_small"))


@pytest.fixture(scope="session")
def full_mock() -> MockData:
    return generate(MockConfig())


def write_csv(path: Path, df: pd.DataFrame, encoding: str = "utf-8") -> Path:
    df.to_csv(path, sep=";", index=False, encoding=encoding)
    return path
