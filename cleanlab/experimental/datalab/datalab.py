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
Implements cleanlab's DataLab interface as a one-stop-shop for tracking
and managing all kinds of issues in datasets.
"""
from __future__ import annotations

import os
import pickle
import warnings
from typing import Any, Dict, List, Mapping, Optional, Union

import datasets
import numpy as np
import pandas as pd
from datasets import load_from_disk
from datasets.arrow_dataset import Dataset

import cleanlab
from cleanlab.experimental.datalab.factory import _IssueManagerFactory
from cleanlab.experimental.datalab.data import Data
from cleanlab.experimental.datalab.data_issues import DataIssues
from cleanlab.experimental.datalab.issue_manager import IssueManager
from cleanlab.experimental.datalab.display import _Displayer
from cleanlab.internal.validation import labels_to_array

__all__ = ["Datalab"]

# Constants:
OBJECT_FILENAME = "datalab.pkl"
ISSUES_FILENAME = "issues.csv"
ISSUE_SUMMARY_FILENAME = "summary.csv"
INFO_FILENAME = "info.pkl"
DATA_DIRNAME = "data"


class Datalab:
    """
    A single object to find all kinds of issues in datasets.
    It tracks intermediate state from certain functions that can be
    re-used across other functions.  This will become the main way 90%
    of users interface with cleanlab library.

    Parameters
    ----------
    data :
        A Hugging Face Dataset object.
    """

    def __init__(
        self,
        data: Dataset,
        label_name: Union[str, list[str]],
    ) -> None:
        self._validate_data(data)
        self._validate_data_and_labels(data, label_name)

        if isinstance(label_name, list):
            raise NotImplementedError("TODO: multi-label support.")

        self._data = Data(data, label_name)  # TODO: Set extracted class instance to self.data
        self.data = self._data._data
        self.data_issues = DataIssues(self._data)
        self._data_hash = self._data._data_hash
        self.label_name = self._data._label_name
        # self.data.set_format(
        #     type="numpy"
        # )  # TODO: figure out if we are setting all features to numpy, maybe exclude label_name?
        self.issues = self.data_issues.issues
        self.issue_summary = self.data_issues.issue_summary
        self._labels, self._label_map = self._data._labels, self._data._label_map
        self.info = self.data_issues.info
        self.cleanlab_version = cleanlab.version.__version__
        self.path = ""
        self.issue_managers: Dict[str, IssueManager] = {}

    def __repr__(self) -> str:
        """What is displayed if user executes: datalab"""
        return _Displayer(self).__repr__()

    def __str__(self) -> str:
        """What is displayed if user executes: print(datalab)"""
        return _Displayer(self).__str__()

    def __getstate__(self) -> dict:
        """Used by pickle to serialize the object.

        We don't want to pickle the issues, since it's just a dataframe and can be exported to
        a human readable format. We can replace it with the file path to the exported file.

        """
        state = self.__dict__.copy()
        save_path = self.path

        # Update the issues to be the path to the exported file.
        state["issues"] = os.path.join(save_path, ISSUES_FILENAME)
        self.issues.to_csv(state["issues"], index=False)

        # Update the issue summary to be the path to the exported file.
        state["issue_summary"] = os.path.join(save_path, ISSUE_SUMMARY_FILENAME)
        self.issue_summary.to_csv(state["issue_summary"], index=False)

        # Save the dataset to disk
        if self.data is not None:
            state["data"] = os.path.join(save_path, DATA_DIRNAME)
            self.data.save_to_disk(state["data"])
        # if self.info is not None:
        #     state["info"] = os.path.join(save_path, INFO_FILENAME)
        #     # Pickle the info dict.
        #     with open(state["info"], "wb") as f:
        #         pickle.dump(self.info, f)

        return state

    def __setstate__(self, state: dict) -> None:
        """Used by pickle to deserialize the object.

        We need to load the issues from the file path.
        """

        save_path = state.get("path", "")
        if save_path:
            issues_path = state["issues"]
            if isinstance(issues_path, str) and os.path.exists(issues_path):
                state["issues"] = pd.read_csv(issues_path)

            issue_summary_path = state["issue_summary"]
            if isinstance(issue_summary_path, str) and os.path.exists(issue_summary_path):
                state["issue_summary"] = pd.read_csv(issue_summary_path)

            data_path = state["data"]
            if isinstance(data_path, str) and os.path.exists(data_path):
                state["data"] = load_from_disk(data_path)

            # info_path = state["info"]
            # if isinstance(info_path, str) and os.path.exists(info_path):
            #     with open(info_path, "r") as f:
            #         state["info"] = pickle.load(f)
        self.__dict__.update(state)

    @property
    def labels(self) -> np.ndarray:
        return self._labels

    @classmethod
    def _validate_version(cls, datalab: "Datalab") -> None:
        current_version = cleanlab.__version__
        datalab_version = datalab.cleanlab_version
        if current_version != datalab_version:
            warnings.warn(
                f"Saved Datalab was created using different version of cleanlab "
                f"({datalab_version}) than current version ({current_version}). "
                f"Things may be broken!"
            )

    def _resolve_required_args(self, pred_probs, features, model):
        """Resolves the required arguments for each issue type.

        This is a helper function that filters out any issue manager that does not have the required arguments.

        This does not consider custom hyperparameters for each issue type.


        Parameters
        ----------
        pred_probs :
            Out-of-sample predicted probabilities made on the data.

        features :
            Name of column containing precomputed embeddings.

        model :
            sklearn compatible model used to compute out-of-sample predicted probabilities for the labels.

        Returns
        -------
        args_dict :
            Dictionary of required arguments for each issue type, if available.
        """
        args_dict = {
            "label": {"pred_probs": pred_probs, "model": model},
            "outlier": {"pred_probs": pred_probs, "features": features},
            "near_duplicate": {"features": features},
        }

        args_dict = {
            k: {k2: v2 for k2, v2 in v.items() if v2 is not None} for k, v in args_dict.items() if v
        }
        args_dict = {k: v for k, v in args_dict.items() if v}

        return args_dict

    def _set_issue_types(
        self,
        issue_types: Optional[Dict[str, Any]],
        required_defaults_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Set necessary configuration for each IssueManager in a dictionary.

        While each IssueManager defines default values for its arguments,
        the Datalab class needs to organize the calls to each IssueManager
        with different arguments, some of which may be

        Parameters
        ----------
        issue_types :
            Dictionary of issue types and argument configuration for their respective IssueManagers.
            If None, then the `required_defaults_dict` is used.

        required_defaults_dict :
            Dictionary of default parameter configuration for each issue type.

        Returns
        -------
        issue_types_copy :
            Dictionary of issue types and their parameter configuration.
            The input `issue_types` is copied and updated with the necessary default values.
        """
        if issue_types is not None:
            issue_types_copy = issue_types.copy()
            self._check_missing_args(required_defaults_dict, issue_types_copy)
        else:
            issue_types_copy = required_defaults_dict.copy()
        # Check that all required arguments are provided.
        self._validate_issue_types_dict(issue_types_copy, required_defaults_dict)

        # Remove None values from argument list, rely on default values in IssueManager
        for key, value in issue_types_copy.items():
            issue_types_copy[key] = {k: v for k, v in value.items() if v is not None}
        return issue_types_copy

    @staticmethod
    def _check_missing_args(required_defaults_dict, issue_types):
        for key, issue_type_value in issue_types.items():
            missing_args = set(required_defaults_dict.get(key, {})) - set(issue_type_value.keys())
            # Impute missing arguments with default values.
            missing_dict = {
                missing_arg: required_defaults_dict[key][missing_arg]
                for missing_arg in missing_args
            }
            issue_types[key].update(missing_dict)

    @staticmethod
    def _validate_issue_types_dict(
        issue_types: Dict[str, Any], required_defaults_dict: Dict[str, Any]
    ) -> None:
        missing_required_args_dict = {}
        for issue_name, required_args in required_defaults_dict.items():
            if issue_name in issue_types:
                missing_args = set(required_args.keys()) - set(issue_types[issue_name].keys())
                if missing_args:
                    missing_required_args_dict[issue_name] = missing_args
        if any(missing_required_args_dict.values()):
            error_message = ""
            for issue_name, missing_required_args in missing_required_args_dict.items():
                error_message += f"Required argument {missing_required_args} for issue type {issue_name} was not provided.\n"
            raise ValueError(error_message)

    def _set_labels(self, label_name: Union[str, list[str]]) -> tuple[np.ndarray, Mapping]:
        """
        Extracts labels from the dataset and stores it in self._labels.

        Parameters
        ----------
        label_name : str or list[str] (TODO)
            Name of the column in the dataset that contains the labels.

        Returns
        -------
        formatted_labels : np.ndarray
            Labels in the format [0, 1, ..., K-1] where K is the number of classes.

        inverse_map : dict
            Mapping from the formatted labels to the original labels in the dataset.
        """

        if isinstance(label_name, list):

            raise NotImplementedError("TODO")

            # _labels = np.vstack([my_data[label] for label in labels]).T

        # Raw values from the dataset
        _labels = self.data[label_name]
        _labels = labels_to_array(_labels)  # type: ignore[assignment]
        if _labels.ndim != 1:
            raise ValueError("labels must be 1D numpy array.")

        unique_labels = np.unique(_labels)
        label_map = {label: i for i, label in enumerate(unique_labels)}
        # labels 0, 1, ..., K-1
        formatted_labels = np.array([label_map[label] for label in _labels])
        inverse_map = {i: label for label, i in label_map.items()}

        return formatted_labels, inverse_map

    @staticmethod
    def _validate_data(data) -> None:
        if isinstance(data, datasets.DatasetDict):
            raise ValueError(
                "Please pass a single dataset, not a DatasetDict. "
                "Try initializing with data['train'] instead."
            )

        assert isinstance(data, Dataset)

    @staticmethod
    def _validate_data_and_labels(data, labels) -> None:
        if isinstance(labels, np.ndarray):
            assert labels.shape[0] == data.shape[0]

        if isinstance(labels, str):
            pass

    def _get_report(self, k: int, verbosity: int) -> str:
        # Sort issues based on the score
        # Show top K issues
        # Show the info (get_info) with some verbosity level
        #   E.g. for label issues, only show the confident joint computed with the health_summary
        issue_type_sorted_keys: List[str] = (
            self.issue_summary.sort_values(by="score", ascending=True)["issue_type"]
            .to_numpy()
            .tolist()
        )
        issue_managers = self._get_managers(issue_type_sorted_keys)
        report_str = ""
        for issue_manager in issue_managers:
            report_str += issue_manager.report(k=k, verbosity=verbosity) + "\n\n"
        return report_str

    def _get_managers(self, keys: List[str]) -> List[IssueManager]:
        issue_managers = [self.issue_managers[i] for i in keys]
        return issue_managers

    def find_issues(
        self,
        *,
        pred_probs: Optional[np.ndarray] = None,
        issue_types: Optional[Dict[str, Any]] = None,
        features: Optional[str] = None,  # embeddings of data
        model=None,  # sklearn.Estimator compatible object  # noqa: F821
    ) -> None:
        """
        Checks for all sorts of issues in the data, including in labels and in features.

        Can utilize either provided model or pred_probs.

        Note
        ----
        The issues are saved in self.issues, but are not returned.

        Parameters
        ----------
        pred_probs :
            Out-of-sample predicted probabilities made on the data.

        issue_types :
            Collection of the types of issues to search for.

        features :
            Name of column containing precomputed embeddings.

            WARNING
            -------
            This is not yet implemented.

        model :
            sklearn compatible model used to compute out-of-sample
            predicted probability for the labels.

            WARNING
            -------
            This is not yet implemented.

        issue_init_kwargs :
            # Add path to IssueManager class docstring.
            Keyword arguments to pass to the IssueManager constructor.

            See Also
            --------
            IssueManager


            It is a dictionary of dictionaries, where the keys are the issue types
            and the values are dictionaries of keyword arguments to pass to the
            IssueManager constructor.

            For example, if you want to pass the keyword argument "clean_learning_kwargs"
            to the constructor of the LabelIssueManager, you would pass:

            .. code-block:: python

                issue_init_kwargs = {
                    "label": {
                        "clean_learning_kwargs": {
                            "prune_method": "prune_by_noise_rate",
                        }
                    }
                }

        """

        required_args_per_issue_type = self._resolve_required_args(pred_probs, features, model)

        issue_types_copy = self._set_issue_types(issue_types, required_args_per_issue_type)

        new_issue_managers = [
            factory(datalab=self, **issue_types_copy.get(factory.issue_name, {}))
            for factory in _IssueManagerFactory.from_list(list(issue_types_copy.keys()))
        ]

        failed_managers = []
        for issue_manager, arg_dict in zip(new_issue_managers, issue_types_copy.values()):
            try:
                issue_manager.find_issues(**arg_dict)
                self.collect_results_from_issue_manager(issue_manager)
            except Exception as e:
                print(f"Error in {issue_manager.issue_name}: {e}")
                failed_managers.append(issue_manager)

        if failed_managers:
            print(f"Failed to find issues for {failed_managers}")
        added_managers = {
            im.issue_name: im for im in new_issue_managers if im not in failed_managers
        }
        self.issue_managers.update(added_managers)

    def collect_results_from_issue_manager(self, issue_manager: IssueManager) -> None:
        """
        Collects results from an IssueManager and update the corresponding
        attributes of the Datalab object.

        This includes:
        - self.issues
        - self.issue_summary
        - self.info

        Parameters
        ----------
        issue_manager :
            IssueManager object to collect results from.
        """
        overlapping_columns = list(set(self.issues.columns) & set(issue_manager.issues.columns))
        if overlapping_columns:
            warnings.warn(
                f"Overwriting columns {overlapping_columns} in self.issues with "
                f"columns from issue manager {issue_manager}."
            )
            self.issues.drop(columns=overlapping_columns, inplace=True)
        self.issues = self.issues.join(issue_manager.issues, how="outer")

        if issue_manager.issue_name in self.issue_summary["issue_type"].values:
            warnings.warn(
                f"Overwriting row in self.issue_summary with "
                f"row from issue manager {issue_manager}."
            )
            self.issue_summary = self.issue_summary[
                self.issue_summary["issue_type"] != issue_manager.issue_name
            ]
        self.issue_summary = pd.concat(
            [self.issue_summary, issue_manager.summary],
            axis=0,
            ignore_index=True,
        )

        if issue_manager.issue_name in self.info:
            warnings.warn(
                f"Overwriting key {issue_manager.issue_name} in self.info with "
                f"key from issue manager {issue_manager}."
            )
        self.info[issue_manager.issue_name] = issue_manager.info

    def get_info(self, issue_name, *subkeys) -> Any:
        """Returns dict of info about a specific issue, or None if this issue does not exist in self.info.
        Internally fetched from self.info[issue_name] and prettified.
        Keys might include: number of examples suffering from issue,
        indicates of top-K examples most severely suffering,
        other misc stuff like which sets of examples are duplicates if the issue=="duplicated".
        """
        if issue_name in self.info:
            info = self.info[issue_name]
            if subkeys:
                for sub_id, subkey in enumerate(subkeys):
                    if not isinstance(info, dict):
                        raise ValueError(
                            f"subkey {subkey} at index {sub_id} is not a valid key in info dict."
                            f"info is {info} and remaining subkeys are {subkeys[sub_id:]}."
                        )
                    sub_info = info.get(subkey)
                    info = sub_info
            return info
        else:
            raise ValueError(
                f"issue_name {issue_name} not found in self.info. These have not been computed yet."
            )
            # could alternatively consider:
            # raise ValueError("issue_name must be a valid key in Datalab.info dict.")

    def report(self, k: int = 5, verbosity: int = 0) -> None:
        """Prints helpful summary of all issues."""
        # Show summary of issues
        print(self._get_report(k=k, verbosity=verbosity))

    def save(self, path: str) -> None:
        """Saves this Lab to file (all files are in folder at path/).
        Uses nice format for the DF attributes (csv) and dict attributes (eg. json if possible).
        We do not guarantee saved Lab can be loaded from future versions of cleanlab.

        You have to save the Dataset yourself if you want it saved to file!
        """

        if os.path.exists(path):
            print(f"WARNING: Existing files will be overwritten by newly saved files at: {path}")
        else:
            os.mkdir(path)

        self.path = path

        object_file = os.path.join(self.path, OBJECT_FILENAME)
        with open(object_file, "wb") as f:
            pickle.dump(self, f)

        print(
            f"Saved Datalab to folder: {path}"
            "The Dataset must be saved/loaded separately "
            "to access it after reloading this Datalab."
        )

    @classmethod
    def load(cls, path: str, data: Optional[Dataset] = None) -> "Datalab":
        """Loads Lab from file. Folder could ideally be zipped or unzipped.
        Checks which cleanlab version Lab was previously saved from
            and raises warning if they dont match.
        `path` is the path to the saved Datalab, not Dataset.

        Dataset should be the same one used before saving.
        If data is None, the self.data attribute of this object
            will be empty and some functionality may not work.
        """
        if not os.path.exists(path):
            raise ValueError(f"No folder found at specified path: {path}")

        object_file = os.path.join(path, OBJECT_FILENAME)
        with open(object_file, "rb") as f:
            datalab = pickle.load(f)

        cls._validate_version(datalab)

        if data is not None:
            if hash(data) != datalab._data_hash:
                raise ValueError(
                    "Data has been modified since Lab was saved. "
                    "Cannot load Lab with modified data."
                )

            if len(data) != len(datalab.labels):
                raise ValueError(
                    f"Length of data ({len(data)}) does not match length of labels ({len(datalab.labels)})"
                )

            datalab.data = data

        return datalab
