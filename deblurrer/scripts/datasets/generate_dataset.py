#!/usr/bin/python
# coding=utf-8

"""
Reads the tf records and put them into a TFRecordDataset.

the tfrecords must be in datasets/ folder

run this script from bash perform a benchmark of the dataset performane

"""

import os
import glob
import time

import tensorflow as tf

AUTOTUNE = tf.data.experimental.AUTOTUNE


def parse(example):
    """
    Parse single example from tfrecord to actual image.

    this fn operates over a single sharp/blur pair
    if you know how to vectorize this, colaborate

    Args:
        example (tf.Tensor): sharp/blur tfrecord encoded strings

    Returns:
        fully parsed, decoded and loaded sharp/blur pair(Rank 4)

    """
    feature_properties = {
        'sharp': tf.io.FixedLenFeature([], tf.string),
        'blur': tf.io.FixedLenFeature([], tf.string),
    }

    example = tf.io.parse_example(example, feature_properties)

    # Decode sharp
    sharp = tf.io.decode_image(example['sharp'], expand_animations=False)

    # Decode blur
    blur = tf.io.decode_image(example['blur'], expand_animations=False)

    example = tf.stack([sharp, blur])

    return example


def transform(example):
    """
    Apply transforms to a batch of sharp/blur pairs.

    This fn is vectorized

    Args:
        example (tf.Tensor): fully parsed, decoded and loaded sharp/blur pair

    Returns:
        batch of transformed sharp/blur pairs tensor(Rank 5)

    """
    # Swaps batch dimension to be second, this make calcs easier in the future
    sharp, blur = tf.unstack(example, axis=1)
    images = tf.concat([sharp, blur], axis=0)

    # Generates a random crop size
    crop_size = int(os.environ.get('IMAGE_SIZE'))
    batch_size = tf.shape(images)[0]

    # Cropping
    images = tf.image.random_crop(
        images,
        size=[batch_size, crop_size, crop_size, 3],
    )

    images = tf.cast(images, dtype=tf.float32)
    images = (images - 127.0) / 128.0

    sharp, blur = tf.split(images, num_or_size_splits=2)
    example = tf.stack([sharp, blur], axis=1)

    return example


def get_dataset(path, name, batch_size=8, use_cache=False):
    """
    Generate an interleaved dataset.

    The dataset is composed of several tfrecords
    named with suffix=name. Ex:

    train_01.tfrecords
    train_02.tfrecords

    with name='train'

    will load all the tfrecords suffixed with 'train' and interleave them

    Args:
        path (str): absolute path to the tfrecords folder
        name (str): suffix name to look for tf records
        batch_size (str): batch size of sub-datasets
        use_cache (bool): Register transformations on cache file

    Returns:
        interleaved dataset composed of all the matching tfrecords

    """
    # Find all the relevant tfrecord following the name suffix
    tfrecs = glob.glob(
        '{path}*.tfrecords'.format(path=os.path.join(path, name)),
    )

    # Creates a dataset listing out tfrecord files
    dataset = tf.data.Dataset.from_tensor_slices(tfrecs)

    # Interleave the tfrecord files contents into a single fast dataset
    dataset = dataset.interleave(
        lambda tfrec: tf.data.TFRecordDataset(tfrec),
        cycle_length=len(tfrecs),
        block_length=batch_size,
        num_parallel_calls=len(tfrecs),
    )

    # Parse, batch and transform
    dataset = dataset.map(parse, num_parallel_calls=AUTOTUNE)
    dataset = dataset.batch(batch_size)
    dataset = dataset.map(transform)

    # Cache transforms
    if (use_cache):
        dataset = dataset.cache(
            os.path.join(path, '{name}_cache'.format(name=name)),
        )

    # Prefetch data
    dataset = dataset.prefetch(AUTOTUNE)

    return dataset


def epoch_time(dataset, num_epochs=1):
    """Benchmark function."""
    start_time = time.perf_counter()
    for _ in range(num_epochs):
        for _ in dataset:
            # Performing a training step
            pass
    tf.print("Execution time for first epoch:", time.perf_counter() - start_time)


def n_batch_time(ds, steps=1000, batch_size=8):
    """Benchmark function."""
    start = time.time()
    it = iter(ds)
    for i in range(steps):
        batch = next(it)
    end = time.time()

    duration = end-start
    print("Execution time for {} batches: {} s".format(steps, duration))
    print("{:0.5f} Images/s".format(batch_size*steps/duration))


def run(path):
    """
    Run the script.

    Run this script from bash perform some benchmarking in the train dataset

    Args:
        path (str): from where to load tfrecords
    """
    dataset = get_dataset(path, 'train', batch_size=8, use_cache=False)

    for exam in dataset.take(1):
        print(exam.shape)

    epoch_time(dataset, 1)

    dataset = dataset.repeat()

    n_batch_time(dataset, 100, batch_size=8)


if (__name__ == '__main__'):
    # Get the path to the datasets folder
    folder_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__),
                    ),
                ),
            ),
        ),
        os.path.join('datasets', 'tfrecords'),
    )

    run(folder_path)
