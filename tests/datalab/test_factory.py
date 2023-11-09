import pytest

from cleanlab.datalab.internal.issue_manager_factory import register, REGISTRY
from cleanlab import Datalab
from cleanlab.datalab.internal.issue_manager.issue_manager import IssueManager


@pytest.fixture
def registry():
    return REGISTRY


def test_list_possible_issue_types(registry):
    issue_types = Datalab.list_possible_issue_types()
    assert isinstance(issue_types, list)
    possible_issues = [
        "label",
        "outlier",
        "near_duplicate",
        "non_iid",
        "class_imbalance",
        "underperforming_group",
        "data_valuation",
    ]
    assert set(issue_types) == set(possible_issues)

    test_key = "test_for_list_possible_issue_types"

    @register
    class TestIssueManager(IssueManager):
        issue_name = test_key

    issue_types = Datalab.list_possible_issue_types()
    assert set(issue_types) == set(
        possible_issues + [test_key]
    ), "New issue type should be added to the list"

    # Clean up
    del registry[test_key]
