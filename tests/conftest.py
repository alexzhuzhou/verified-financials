"""Shared test fixtures."""

from __future__ import annotations

import pytest

from verified_financials import datagen
from verified_financials.config.loader import load_config
from verified_financials.loaders.base import load_all
from verified_financials.store.db import connect, init_schema
from verified_financials.store.repository import FactRepository


@pytest.fixture(scope="session")
def config():
    return load_config()


@pytest.fixture
def data_dir(tmp_path, config):
    datagen.generate(data_dir=tmp_path, seed=config.settings.random_seed)
    return tmp_path


@pytest.fixture
def repo(data_dir, config):
    conn = connect(":memory:")
    init_schema(conn)
    repository = FactRepository(conn)
    repository.add_many(load_all(data_dir, config.facility.as_of_date))
    return repository


@pytest.fixture(scope="session")
def stress_config():
    return load_config("config_advanced.yaml")


@pytest.fixture
def stress_data_dir(tmp_path, stress_config):
    datagen.generate(
        data_dir=tmp_path, seed=stress_config.settings.random_seed, scenario="stress"
    )
    return tmp_path


@pytest.fixture
def stress_repo(stress_data_dir, stress_config):
    conn = connect(":memory:")
    init_schema(conn)
    repository = FactRepository(conn)
    repository.add_many(load_all(stress_data_dir, stress_config.facility.as_of_date))
    return repository
