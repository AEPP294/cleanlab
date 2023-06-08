# Copyright (C) 2017-2023  Cleanlab Inc.
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
Scripts to test cleanlab.segmentation package
"""
import numpy as np

# import matplotlib.pyplot as plt
# import os
import numpy as np
import random

np.random.seed(0)
import pytest
from cleanlab.internal.multilabel_scorer import softmin


# Filter
from cleanlab.segmentation.filter import (
    find_label_issues,
    _check_input,
)

# Rank
from cleanlab.segmentation.rank import (
    get_label_quality_scores,
    issues_from_scores,
    _get_label_quality_per_image,
)

# Summary
from cleanlab.segmentation.summary import (
    display_issues,
    common_label_issues,
    filter_by_class,
    _generate_colormap,
)


def generate_three_image_dataset(bad_index):
    good_gt = np.zeros((10, 10))
    good_gt[:5, :] = 1.0
    bad_gt = np.ones((10, 10))
    bad_gt[:5, :] = 0.0
    good_pr = np.random.random((2, 10, 10))
    good_pr[0, :5, :] = good_pr[0, :5, :] / 10
    good_pr[1, 5:, :] = good_pr[1, 5:, :] / 10

    val = np.binary_repr([4, 2, 1][bad_index], width=3)
    error = [int(case) for case in val]

    labels = []
    pred = []
    for case in val:
        if case == "0":
            labels.append(good_gt)
            pred.append(good_pr)
        else:
            labels.append(bad_gt)
            pred.append(good_pr)

    labels = np.array(labels)
    pred_probs = np.array(pred)
    return labels, pred_probs, error


labels, pred_probs, error = generate_three_image_dataset(random.randint(0, 2))
labels, pred_probs = labels.astype(int), pred_probs.astype(float)
num_images, num_classes, h, w = pred_probs.shape


def test_find_label_issues():
    issues = find_label_issues(labels, pred_probs, downsample=1, n_jobs=None, batch_size=1000)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    issues = find_label_issues(labels, pred_probs, downsample=2, batch_size=1739)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    issues = find_label_issues(labels, pred_probs, downsample=5, n_jobs=None, batch_size=2838)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    with pytest.raises(Exception) as e:
        issues = find_label_issues(labels, pred_probs, downsample=4, n_jobs=None, batch_size=1000)

    # Simple tests
    # Test case 1: Test with larger batch_size
    issues = find_label_issues(labels, pred_probs, downsample=1, n_jobs=None, batch_size=2000)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    # Test case 2: Test with smaller batch_size
    issues = find_label_issues(labels, pred_probs, downsample=1, n_jobs=None, batch_size=500)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    # Test case 3: Test verbose off
    issues = find_label_issues(labels, pred_probs, downsample=1, verbose=False)

    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    # Test case 4: Test with scores_only parameter
    scores = find_label_issues(labels, pred_probs, downsample=1, n_jobs=None, scores_only=True)
    assert np.argmax(error) == np.argmin(scores)

    # Test case 5: Test with invalid downsample value
    with pytest.raises(Exception) as e:
        issues = find_label_issues(labels, pred_probs, downsample=3, n_jobs=None, batch_size=1000)

    # Test case 6: Test with n_jobs parameter
    issues = find_label_issues(labels, pred_probs, downsample=1, n_jobs=2, batch_size=1000)
    assert np.argmax(error) == np.argmax(issues.sum((1, 2)))

    # Test case 7: Test with invalid labels
    with pytest.raises(Exception) as e:
        issues = find_label_issues(
            np.array([[[[1, 2, 3]]]]), pred_probs, downsample=1, n_jobs=None, batch_size=1000
        )

    # Test case 8: Test with invalid pred_probs
    with pytest.raises(Exception) as e:
        issues = find_label_issues(
            labels, np.array([[[[0.1, 0.2, 0.3]]]]), downsample=1, n_jobs=None, batch_size=1000
        )


def test__check_input():
    bad_gt = np.random.random((5, 10, 20))
    with pytest.raises(Exception) as e:
        _check_input(bad_gt, bad_gt)

    bad_pr = np.random.random((5, 2, 10, 20))
    with pytest.raises(Exception) as e:
        _check_input(bad_pr, bad_pr)

    smaller_pr = np.random.random((5, 2, 9, 20))
    with pytest.raises(Exception) as e:
        _check_input(bad_gt, smaller_pr)

    fewer_gt = np.random.random((4, 10, 20))
    with pytest.raises(Exception) as e:
        _check_input(fewer_gt, smaller_pr)


def test_get_label_quality_scores():
    image_scores_softmin, pixel_scores = get_label_quality_scores(
        labels, pred_probs, method="softmin"
    )
    assert np.argmax(error) == np.argmin(image_scores_softmin)

    with pytest.raises(Exception) as e:
        get_label_quality_scores(labels, pred_probs, method="num_pixel_issues", downsample=4)

    with pytest.raises(Exception) as e:
        get_label_quality_scores(labels, pred_probs, method="num_pixel_issues")
    image_scores_npi, pixel_scores = get_label_quality_scores(
        labels, pred_probs, method="num_pixel_issues", downsample=1
    )

    assert np.argmax(error) == np.argmin(image_scores_npi)

    with pytest.raises(Exception):
        get_label_quality_scores(labels, pred_probs, method="invalid_method")

    image_scores_softmin, pixel_scores = get_label_quality_scores(
        labels, pred_probs, downsample=1, method="softmin"
    )
    assert len(image_scores_softmin) == labels.shape[0]
    assert pixel_scores.shape == labels.shape

    with pytest.raises(ValueError):
        get_label_quality_scores(labels, pred_probs, method="num_pixel_issues", batch_size=-1)
        get_label_quality_scores(
            labels, pred_probs, method="num_pixel_issues", downsample=1, batch_size=0
        )


# Testing issues from scores
def test_issues_from_scores():
    image_scores_softmin, pixel_scores = get_label_quality_scores(
        labels, pred_probs, method="softmin"
    )
    issues_from_score = issues_from_scores(image_scores_softmin, pixel_scores, threshold=1)
    assert np.shape(issues_from_score) == np.shape(pixel_scores)
    assert h * w * num_images == issues_from_score.sum()

    issues_from_score = issues_from_scores(image_scores_softmin, pixel_scores, threshold=0)
    assert 0 == issues_from_score.sum()

    issues_from_score = issues_from_scores(image_scores_softmin, pixel_scores, threshold=0.5)
    assert np.argmax(error) == np.argmax(issues_from_score.sum((1, 2)))

    sort_by_score = issues_from_scores(image_scores_softmin, threshold=0.5)
    assert error[sort_by_score[0]] == 1


def test_issues_from_scores_no_pixel_scores():
    # Test if function works correctly when pixel_scores is None
    image_scores_softmin, _ = get_label_quality_scores(labels, pred_probs, method="softmin")
    issues_from_score_result = issues_from_scores(image_scores_softmin, None, threshold=1)
    assert np.shape(issues_from_score_result) == (num_images,)


def test_issues_from_scores_various_thresholds():
    # Test if function works correctly for various values of threshold
    image_scores_softmin, pixel_scores = get_label_quality_scores(
        labels, pred_probs, method="softmin"
    )
    for threshold in [0.1, 0.5, 0.9]:
        issues_from_score_result = issues_from_scores(
            image_scores_softmin, pixel_scores, threshold=threshold
        )
        assert np.all(issues_from_score_result == (pixel_scores < threshold))


def test_issues_from_scores_invalid_inputs():
    # Test if function raises exception when input parameters are invalid
    with pytest.raises(ValueError):
        issues_from_scores(None)
    with pytest.raises(ValueError):
        issues_from_scores(np.array([0.1, 0.2, 0.3]), threshold=1.1)  # Threshold more than 1
    with pytest.raises(ValueError):
        issues_from_scores(np.array([0.1, 0.2, 0.3]), threshold=-0.1)  # Threshold less than 0


def test_issues_from_scores_different_input_sizes():
    # Test if function works correctly for different sizes of input arrays
    for num_images in range(1, 5):
        image_scores = np.random.rand(num_images)
        pixel_scores = np.random.rand(num_images, 100, 100)
        issues_from_score_result = issues_from_scores(image_scores, pixel_scores, threshold=0.5)
        assert np.shape(issues_from_score_result) == np.shape(pixel_scores)


def test_issues_from_scores_sorting():
    # Test if function correctly sorts image_scores
    image_scores_softmin, _ = get_label_quality_scores(labels, pred_probs, method="softmin")
    issues_from_score_result = issues_from_scores(image_scores_softmin, None, threshold=0.5)
    assert np.all(np.sort(image_scores_softmin) == image_scores_softmin[issues_from_score_result])


def test__get_label_quality_per_image():
    # Test when pixel_scores is a random list of 100 values, method is "softmin", and temperature is random
    random_score_array = np.random.random((100,))
    temp = random.random()
    score = _get_label_quality_per_image(random_score_array, method="softmin", temperature=temp)

    cleanlab_softmin = softmin(
        np.expand_dims(random_score_array, axis=0), axis=1, temperature=temp
    )[0]
    assert cleanlab_softmin == score, "Expected cleanlab_softmin to be equal to score"

    # Test when pixel_scores is an empty list, should raise an error
    empty_score_array = np.array([])
    with pytest.raises(Exception) as e:
        _get_label_quality_per_image(empty_score_array, method="softmin", temperature=temp)

    # Test when method is None
    with pytest.raises(Exception):
        _get_label_quality_per_image(random_score_array, method=None, temperature=temp)

    # Test when method is not "softmin", should raise an exception
    with pytest.raises(Exception):
        _get_label_quality_per_image(random_score_array, method="invalid_method", temperature=temp)

    #     Test when temperature is 0, should raise an error
    with pytest.raises(Exception):
        _get_label_quality_per_image(random_score_array, method="softmin", temperature=0)

    with pytest.raises(Exception):
        _get_label_quality_per_image(random_score_array, method="softmin", temperature=None)