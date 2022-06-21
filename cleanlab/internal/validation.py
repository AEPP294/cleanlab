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

import warnings
import numpy as np
import pandas as pd
from sklearn.utils import check_X_y


def assert_valid_inputs(X, y, pred_probs=None):
    """Checks that X, labels, and pred_probs are correctly formatted"""
    if not isinstance(y, (list, np.ndarray, np.generic, pd.Series, pd.DataFrame)):
        raise TypeError("labels should be a numpy array or pandas Series.")
    y = labels_to_array(y)
    assert_valid_class_labels(y)
    allow_empty_X = False if pred_probs is None else True
    if not allow_empty_X:
        assert_nonempty_input(X)
        try:
            n = len(X)
            len_supported = True
        except:
            len_supported = False
        if not len_supported:
            try:
                n = X.shape[0]
                shape_supported = True
            except:
                shape_supported = False
        if (not len_supported) and (not shape_supported):
            raise TypeError("Features object X must support either: len(X) or X.shape[0]")

        if n != len(y):
            raise ValueError("length of X must match length of labels.")

        if n < 2:
            raise ValueError("length of X must be at least 2.")

        assert_indexing_works(X, length_X=n)

    if pred_probs is not None:
        if not isinstance(pred_probs, (np.ndarray, np.generic)):
            raise TypeError("pred_probs must be a numpy array.")
        if len(pred_probs) != len(y):
            raise ValueError("pred_probs and labels must have same length.")
        # Check for valid probabilities.
        if (pred_probs < 0).any() or (pred_probs > 1).any():
            raise ValueError("Values in pred_probs must be between 0 and 1.")
        if X is not None:
            warnings.warn("When X and pred_probs are both provided, former may be ignored.")


def assert_valid_class_labels(y):
    """Check that labels is zero-indexed (first label is 0) and all classes present"""
    if y.ndim != 1:
        raise ValueError("labels must by 1D numpy array.")

    unique_classes = np.unique(y)
    if all(unique_classes != np.arange(len(unique_classes))):
        msg = "cleanlab requires zero-indexed labels (0,1,2,..,K-1), but in "
        msg += "your case: np.unique(labels) = {}".format(str(unique_classes))
        raise TypeError(msg)


def assert_nonempty_input(X):
    if X is None:
        raise ValueError("X cannot be None.")


def assert_indexing_works(X, idx=None, length_X=None):
    """Ensures we can do list-based indexing into X and y"""
    if idx is None:
        if length_X is None:
            length_X = 2

        idx = [0, length_X - 1]
    try:
        if isinstance(X, (pd.DataFrame, pd.Series)):
            _ = X.iloc[idx]
        else:
            _ = X[idx]
    except:
        msg = "Features object X must support list-based indexing; i.e. one of these must work: \n"
        msg += "1)  X[index_list] where say index_list = [0,1,3,10], or \n"
        msg += "2)  X.iloc[index_list] if X is pandas DataFrame."
        raise TypeError(msg)


def labels_to_array(y):
    """Converts different types of label objects to 1D numpy array and checks validity"""
    if isinstance(y, pd.Series):
        y = y.values
    elif isinstance(y, pd.DataFrame):
        y = y.values
        if y.shape[1] != 1:
            raise ValueError("labels must be one dimensional.")
        y = y.flatten()
    elif isinstance(y, list):
        try:
            y = np.array(y)
        except:
            raise ValueError(
                "List of labels must be convertable to 1D numpy array via: np.array(labels)"
            )

    return y
