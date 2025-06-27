import time
from unittest import mock

import pytest

@pytest.fixture
def mock_sleep():
    with mock.patch('time.sleep', mock.MagicMock()) as mocked_sleep:
        yield mocked_sleep

def test_something(mock_sleep):
    time.sleep(3)
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 3

def test_something_else(mock_sleep):
    time.sleep(5)
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 5
