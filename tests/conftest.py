import pytest
import respx


@pytest.fixture
def tmp_config_path(tmp_path):
    return tmp_path / ".sumosearch"


@pytest.fixture
def respx_mock():
    with respx.mock() as mock:
        yield mock
