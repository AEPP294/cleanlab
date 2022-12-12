"""
Helper function internally used in cleanlab.regression
"""

import numpy as np


def assert_valid_inputs(
    labels: np.ndarray,
    predictions: np.ndarray,
    method: str,
) -> None:
    """Checks that ``labels``, ``pred_labels``, ``method`` are correctly formatted."""

    # Check if labels and pred_labels are np.ndarray
    if not isinstance(labels, np.ndarray) or not isinstance(predictions, np.ndarray):
        raise TypeError("labels and pred_labels must be of type np.ndarray")

    # Check if labels and pred_labels are of same shape
    assert (
        labels.shape == predictions.shape
    ), f"shape of label {labels.shape} and predicted labels {predictions.shape} are not same."

    # Check if method passed is string
    if not isinstance(method, str):
        raise TypeError(
            f"Passed method is not of correct type. Expected string, got {type(method)}"
        )
