import pytest
from test_direct_post import test_registration_login

@pytest.fixture
def token():
    return test_registration_login()
