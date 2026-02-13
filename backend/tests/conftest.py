"""
Pytest configuration and shared fixtures.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Resolve repository root (two levels up from backend/)
REPO_ROOT = backend_dir.parent
POLICY_DIR = REPO_ROOT / "docs" / "policies"

import pytest
from policy import PolicyLoader

@pytest.fixture
def policy_dir():
    """Return path to policy directory."""
    return POLICY_DIR

@pytest.fixture
def all_policy_files(policy_dir):
    """Return list of all policy JSON files."""
    return list(policy_dir.glob("*.json"))

@pytest.fixture
def balanced_policy():
    """Load balanced_v1 policy for testing."""
    PolicyLoader._policy = None
    return PolicyLoader.load_policy("balanced_v1")

@pytest.fixture
def required_dimensions():
    """Return list of required dimensions."""
    return PolicyLoader.REQUIRED_DIMENSIONS
