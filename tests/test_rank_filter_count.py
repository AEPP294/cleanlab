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

from __future__ import (
    print_function, absolute_import, division, unicode_literals,
    with_statement, )

from cleanlab import count, filter
from cleanlab.latent_algebra import compute_inv_noise_matrix
from cleanlab.noise_generation import generate_noise_matrix_from_trace
from cleanlab.noise_generation import generate_noisy_labels
from cleanlab.util import value_counts
import numpy as np
import scipy
import pytest


def make_data(
        sparse=False,
        means=[[3, 2], [7, 7], [0, 8]],
        covs=[[[5, -1.5], [-1.5, 1]], [[1, 0.5], [0.5, 4]], [[5, 1], [1, 5]]],
        sizes=[80, 40, 40],
        avg_trace=0.8,
        seed=1,  # set to None for non-reproducible randomness
):
    np.random.seed(seed=seed)

    m = len(means)  # number of classes
    n = sum(sizes)
    local_data = []
    labels = []
    test_data = []
    test_labels = []

    for idx in range(m):
        local_data.append(np.random.multivariate_normal(
            mean=means[idx], cov=covs[idx], size=sizes[idx]))
        test_data.append(np.random.multivariate_normal(
            mean=means[idx], cov=covs[idx], size=sizes[idx]))
        labels.append(np.array([idx for i in range(sizes[idx])]))
        test_labels.append(np.array([idx for i in range(sizes[idx])]))
    X_train = np.vstack(local_data)
    y_train = np.hstack(labels)
    X_test = np.vstack(test_data)
    y_test = np.hstack(test_labels)

    if sparse:
        X_train = scipy.sparse.csr_matrix(X_train)
        X_test = scipy.sparse.csr_matrix(X_test)

    # Compute p(y=k)
    py = np.bincount(y_train) / float(len(y_train))

    noise_matrix = generate_noise_matrix_from_trace(
        m,
        trace=avg_trace * m,
        py=py,
        valid_noise_matrix=True,
        seed=seed,
    )

    # Generate our noisy labels using the noise_matrix.
    s = generate_noisy_labels(y_train, noise_matrix)
    ps = np.bincount(s) / float(len(s))

    # Compute inverse noise matrix
    inv = compute_inv_noise_matrix(py, noise_matrix, ps)

    # Estimate psx
    latent = count.estimate_py_noise_matrices_and_cv_pred_proba(
        X=X_train,
        s=s,
        cv_n_folds=3,
    )

    return {
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
        "s": s,
        "ps": ps,
        "py": py,
        "noise_matrix": noise_matrix,
        "inverse_noise_matrix": inv,
        "est_py": latent[0],
        "est_nm": latent[1],
        "est_inv": latent[2],
        "cj": latent[3],
        "psx": latent[4],
        "m": m,
        "n": n,
    }


# Global to be used by all test methods.
# Only compute this once for speed.
seed = 1
data = make_data(sparse=False, seed=1)

# Create some simple data to test
psx_ = np.array([
    [0.9, 0.1, 0],
    [0.6, 0.2, 0.2],
    [0.1, 0, 0.9],
    [0.1, 0.8, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.1, 0.8],
])
s_ = np.array([0, 0, 1, 1, 1, 1, 1, 1, 1, 2])


def test_exact_prune_count():
    remove = 5
    s = data['s']
    noise_idx = filter.find_label_issues(
        s=s,
        psx=data['psx'],
        num_to_remove_per_class=remove,
        prune_method='prune_by_class',
    )
    assert (all(value_counts(s[noise_idx]) == remove))


@pytest.mark.parametrize("n_jobs", [None, 1, 2])
def test_pruning_both(n_jobs):
    remove = 5
    s = data['s']
    class_idx = filter.find_label_issues(
        s=s,
        psx=data['psx'],
        num_to_remove_per_class=remove,
        prune_method='prune_by_class',
        n_jobs=n_jobs,
    )
    nr_idx = filter.find_label_issues(
        s=s,
        psx=data['psx'],
        num_to_remove_per_class=remove,
        prune_method='prune_by_noise_rate',
        n_jobs=n_jobs,
    )
    both_idx = filter.find_label_issues(
        s=s,
        psx=data['psx'],
        num_to_remove_per_class=remove,
        prune_method='both',
        n_jobs=n_jobs,
    )
    assert (all(s[both_idx] == s[class_idx & nr_idx]))


@pytest.mark.parametrize("prune_method", ['prune_by_noise_rate', 'prune_by_class', 'both',
                                          'confident_learning_off_diagonals',
                                          'argmax_not_equal_given_label'])
def test_prune_on_small_data(prune_method):
    data = make_data(sizes=[1, 1, 1])
    noise_idx = filter.find_label_issues(
        s=data['s'],
        psx=data['psx'],
        prune_method=prune_method,
    )
    # Num in each class < 5. Nothing should be pruned.
    assert (not any(noise_idx))


def test_cj_from_probs():
    cj = count.estimate_confident_joint_from_probabilities(
        s=data["s"],
        psx=data["psx"],
        force_ps=10,
    )
    true_ps = data["ps"] * data["n"]
    forced = cj.sum(axis=1)

    cj = count.estimate_confident_joint_from_probabilities(
        s=data["s"],
        psx=data["psx"],
        force_ps=1,
    )
    forced1 = cj.sum(axis=1)

    cj = count.estimate_confident_joint_from_probabilities(
        s=data["s"],
        psx=data["psx"],
        force_ps=False,
    )
    regular = cj.sum(axis=1)
    # Forcing ps should make ps more similar to the true ps.
    assert (np.mean(true_ps - forced) <= np.mean(true_ps - regular))
    # Check that one iteration is the same as not forcing ps
    assert (np.mean(true_ps - forced1) - np.mean(true_ps - regular) < 2e-4)


def test_calibrate_joint():
    cj = count.compute_confident_joint(
        s=data["s"],
        psx=data["psx"],
        calibrate=False,
    )
    calibrated_cj = count.calibrate_confident_joint(
        s=data["s"],
        confident_joint=cj,
    )
    s_counts = np.bincount(data["s"])

    # Check calibration
    assert (all(calibrated_cj.sum(axis=1).round().astype(int) == s_counts))
    assert (len(data["s"]) == int(round(np.sum(calibrated_cj))))

    calibrated_cj2 = count.compute_confident_joint(
        s=data["s"],
        psx=data["psx"],
        calibrate=True,
    )

    # Check equivalency
    assert (np.all(calibrated_cj == calibrated_cj2))


def test_estimate_joint():
    joint = count.estimate_joint(
        s=data["s"],
        psx=data["psx"],
    )

    # Check that jjoint sums to 1.
    assert (abs(np.sum(joint) - 1.) < 1e-6)


def test_compute_confident_joint():
    cj = count.compute_confident_joint(
        s=data["s"],
        psx=data["psx"],
    )

    # Check that confident joint doesn't overcount number of examples.
    assert (np.sum(cj) <= data["n"])
    # Check that confident joint is correct shape
    assert (np.shape(cj) == (data["m"], data["m"]))


def test_cj_from_probs():
    with pytest.warns(UserWarning) as w:
        cj = count.estimate_confident_joint_from_probabilities(
            s=data["s"],
            psx=data["psx"],
            force_ps=10,
        )
        true_ps = data["ps"] * data["n"]
        forced = cj.sum(axis=1)

        cj = count.estimate_confident_joint_from_probabilities(
            s=data["s"],
            psx=data["psx"],
            force_ps=1,
        )
        forced1 = cj.sum(axis=1)

        cj = count.estimate_confident_joint_from_probabilities(
            s=data["s"],
            psx=data["psx"],
            force_ps=False,
        )
        regular = cj.sum(axis=1)
        # Forcing ps should make ps more similar to the true ps.
        assert (np.mean(true_ps - forced) <= np.mean(true_ps - regular))
        # Check that one iteration is the same as not forcing ps
        assert (np.mean(true_ps - forced1) - np.mean(true_ps - regular) < 2e-4)


def test_estimate_latent_py_method():
    for py_method in ["cnt", "eqn", "marginal"]:
        py, nm, inv = count.estimate_latent(
            confident_joint=data['cj'],
            s=data['s'],
            py_method=py_method,
        )
        assert (sum(py) - 1 < 1e-4)
    try:
        py, nm, inv = count.estimate_latent(
            confident_joint=data['cj'],
            s=data['s'],
            py_method='INVALID',
        )
    except ValueError as e:
        assert ('should be' in str(e))
        with pytest.raises(ValueError) as e:
            py, nm, inv = count.estimate_latent(
                confident_joint=data['cj'],
                s=data['s'],
                py_method='INVALID',
            )


def test_estimate_latent_converge():
    py, nm, inv = count.estimate_latent(
        confident_joint=data['cj'],
        s=data['s'],
        converge_latent_estimates=True,
    )

    py2, nm2, inv2 = count.estimate_latent(
        confident_joint=data['cj'],
        s=data['s'],
        converge_latent_estimates=False,
    )
    # Check results are similar, but not the same.
    assert (np.any(inv != inv2))
    assert (np.any(py != py2))
    assert (np.all(abs(py - py2) < 0.1))
    assert (np.all(abs(nm - nm2) < 0.1))
    assert (np.all(abs(inv - inv2) < 0.1))


@pytest.mark.parametrize("sparse", [True, False])
def test_estimate_noise_matrices(sparse):
    data = make_data(sparse=sparse, seed=seed)
    nm, inv = count.estimate_noise_matrices(
        X=data["X_train"],
        s=data["s"],
    )
    assert (np.all(abs(nm - data["est_nm"]) < 0.1))
    assert (np.all(abs(inv - data["est_inv"]) < 0.1))


def test_pruning_reduce_prune_counts():
    """Make sure it doesnt remove when its not supposed to"""
    cj = np.array([
        [325, 16, 22],
        [47, 178, 10],
        [36, 8, 159],
    ])
    cj2 = filter.reduce_prune_counts(cj, frac_noise=1.0)
    assert (np.all(cj == cj2))


def test_pruning_keep_at_least_n_per_class():
    """Make sure it doesnt remove when its not supposed to"""
    cj = np.array([
        [325, 16, 22],
        [47, 178, 10],
        [36, 8, 159],
    ])
    prune_count_matrix = filter.keep_at_least_n_per_class(
        prune_count_matrix=cj.T,
        n=5,
    )
    assert (np.all(cj == prune_count_matrix.T))


def test_pruning_order_method():
    order_methods = ["prob_given_label", "normalized_margin"]
    results = []
    for method in order_methods:
        results.append(filter.find_label_issues(
            s=data['s'],
            psx=data['psx'],
            sorted_index_method=method,
        ))
    assert (len(results[0]) == len(results[1]))


@pytest.mark.parametrize("multi_label", [True, False])
@pytest.mark.parametrize("prune_method", ['prune_by_noise_rate', 'prune_by_class', 'both',
                                          'confident_learning_off_diagonals'])
def test_get_noise_indices_multi_label(multi_label, prune_method):
    s_ml = [[z, data['y_train'][i]] for i, z in enumerate(data['s'])]
    noise_idx = filter.find_label_issues(
        s=s_ml if multi_label else data['s'],
        psx=data['psx'],
        prune_method=prune_method,
        multi_label=multi_label,
    )
    acc = np.mean((data['s'] != data['y_train']) == noise_idx)
    # Make sure cleanlab does reasonably well finding the errors.
    # acc is the accuracy of detecting a label error.
    assert (acc > 0.85)


def test_confident_learning_off_diagonals_prune_method():
    cj, indices = count.compute_confident_joint(
        s=data["s"],
        psx=data["psx"],
        calibrate=False,
        return_indices_of_off_diagonals=True,
    )
    # Check that the number of 'label errors' found in off diagonals
    # matches the off diagonals of the uncalibrated confident joint
    assert (len(indices) == (np.sum(cj) - np.trace(cj)))


def test_argmax_not_equal_given_label_prune_method():
    psx = np.array([
        [0.9, 0.1, 0],
        [0.6, 0.2, 0.2],
        [0.3, 0.3, 4],
        [0.1, 0.1, 0.8],
        [0.4, 0.5, 0.1],
    ])
    s = np.array([0, 0, 1, 1, 2])
    label_errors = filter.baseline_argmax(psx, s)
    assert (all(label_errors == [False, False, True, True, True]))

    label_errors = filter.baseline_argmax(psx_, s_)
    assert (all(label_errors == np.array([False, False, True, False,
                                          False, False, False, False, False, False])))


@pytest.mark.parametrize("calibrate", [True, False])
@pytest.mark.parametrize("prune_method", ['prune_by_noise_rate',
                                          'prune_by_class', 'both'])
def test_find_label_issues_using_argmax_confusion_matrix(calibrate, prune_method):
    label_errors = filter.baseline_argmax_confusion_matrix(
        psx_, s_, calibrate=calibrate, prune_method=prune_method)
    assert (all(label_errors == np.array([False, False, True, False,
                                          False, False, False, False, False, False])))