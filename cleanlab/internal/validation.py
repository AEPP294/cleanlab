# Copyright (C) 2017-2022  Cleanlab Inc.
# This file is part of cleanlab.
#
# cleanlab is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cleanlab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with cleanlab.  If not, see <https://www.gnu.org/licenses/>.

"""
Checks to ensure valid inputs for various methods.
"""

from typing import Any, List, Optional, Union
import warnings
import numpy as np
import pandas as pd


def assert_valid_inputs(
    X: Any,
    y: Union[list, np.ndarray, pd.Series, pd.DataFrame],
    pred_probs: Optional[np.ndarray] = None,
    multi_label: bool = False,
) -> None:
    """Checks that X, labels, and pred_probs are correctly formatted"""
    if not isinstance(y, (list, np.ndarray, np.generic, pd.Series, pd.DataFrame)):
        raise TypeError("labels should be a numpy array or pandas Series.")
    if not multi_label:
        y = labels_to_array(y)
        assert_valid_class_labels(y)

    allow_empty_X = False if pred_probs is None else True
    if not allow_empty_X:
        assert_nonempty_input(X)
        try:
            num_examples = len(X)
            len_supported = True
        except:
            len_supported = False
        if not len_supported:
            try:
                num_examples = X.shape[0]
                shape_supported = True
            except:
                shape_supported = False
        if (not len_supported) and (not shape_supported):
            raise TypeError("Data features X must support either: len(X) or X.shape[0]")

        if num_examples != len(y):
            raise ValueError(
                f"X and labels must be same length, but X is length {num_examples} and labels is length {len(y)}."
            )

        assert_indexing_works(X, length_X=num_examples)

    if pred_probs is not None:
        if not isinstance(pred_probs, (np.ndarray, np.generic)):
            raise TypeError("pred_probs must be a numpy array.")
        if len(pred_probs) != len(y):
            raise ValueError("pred_probs and labels must have same length.")
        if len(pred_probs.shape) != 2:
            raise ValueError("pred_probs array must have shape: num_examples x num_classes.")
        # Check for valid probabilities.
        if (np.min(pred_probs) < 0) or (np.max(pred_probs) > 1):
            raise ValueError("Values in pred_probs must be between 0 and 1.")
        if X is not None:
            warnings.warn("When X and pred_probs are both provided, former may be ignored.")
        if not multi_label:  # TODO: can remove this clause once missing classes are supported
            num_unique_labels = len(np.unique(y))
            if num_unique_labels != pred_probs.shape[1]:
                raise ValueError(
                    "All classes in (0,1,2,...,K-1) must be present in labels "
                    f"with K = pred_probs.shape[1] = {pred_probs.shape[1]} in your case, "
                    f"but your labels only contain {num_unique_labels} unique values."
                )


def assert_valid_class_labels(y: np.ndarray) -> None:
    """Check that labels is zero-indexed (first label is 0) and all classes present.
    Assumes labels is 1D numpy array (not multi-label).
    """
    if y.ndim != 1:
        raise ValueError("labels must be 1D numpy array.")

    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        raise ValueError("Labels must contain at least 2 classes.")

    if (unique_classes != np.arange(len(unique_classes))).any():
        msg = "cleanlab requires zero-indexed integer labels (0,1,2,..,K-1), but in "
        msg += "your case: np.unique(labels) = {}. ".format(str(unique_classes))
        msg += "Every class in (0,1,2,..,K-1) must be present in labels as well."
        raise TypeError(msg)


def assert_nonempty_input(X: Any) -> None:
    if X is None:
        raise ValueError("Data features X cannot be None. Currently X is None.")


def assert_indexing_works(
    X: Any, idx: Optional[List[int]] = None, length_X: Optional[int] = None
) -> None:
    """Ensures we can do list-based indexing into ``X`` and ``y``.
    length_X is argument passed in since sparse matrix ``X``
    does not support: ``len(X)`` and we want this method to work for sparse ``X``
    (in addition to many other types of ``X``).
    """
    if idx is None:
        if length_X is None:
            length_X = 2  # pragma: no cover

        idx = [0, length_X - 1]
    try:
        if isinstance(X, (pd.DataFrame, pd.Series)):
            _ = X.iloc[idx]
        else:
            _ = X[idx]
    except:
        msg = "Data features X must support list-based indexing; i.e. one of these must work: \n"
        msg += "1)  X[index_list] where say index_list = [0,1,3,10], or \n"
        msg += "2)  X.iloc[index_list] if X is pandas DataFrame."
        raise TypeError(msg)


def labels_to_array(y: Union[list, np.ndarray, np.generic, pd.Series, pd.DataFrame]) -> np.ndarray:
    """Converts different types of label objects to 1D numpy array and checks validity

    Parameters
    ----------
    y : Union[list, np.ndarray, pd.Series, pd.DataFrame]
        Labels to convert to 1D numpy array. Can be a list, numpy array, pandas Series, or pandas DataFrame.

    Returns
    -------
    np.ndarray
        1D numpy array of labels.
    """
    if isinstance(y, pd.Series):
        return np.asarray(y.values)
    elif isinstance(y, pd.DataFrame):
        y = y.values
        if y.shape[1] != 1:
            raise ValueError("labels must be one dimensional.")
        return y.flatten()
    else:  # y is list, np.array, or some other tuple-like object
        try:
            return np.asarray(y)
        except:
            raise ValueError(
                "List of labels must be convertable to 1D numpy array via: np.array(labels)."
            )
