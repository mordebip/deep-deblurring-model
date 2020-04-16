#!/usr/bin/python
# coding=utf-8

"""Defines the custom callbacks used at train time."""

from datetime import datetime

import tensorflow as tf


class SaveImageToDisk(tf.keras.callbacks.Callback):
    """
    This callback saves to disk an image generated by generator.

    Serves as visual performance proof of the model
    """
    def __init__(self, path, test_image):
        """
        Init the callback.

        Args:
            path (str): folder where the results will be saved
            test_image (str): image pair tensor for test, shape [2, h, w, 3]
        """
        self.path = path

        sharp_image, blur_image = tf.split(test_image, 2)
        self.sharp_image = sharp_image
        self.blur_image = blur_image

    def on_epoch_end(self, epoch, logs=None):
        """Generate and save image to disk."""
        
        image = self.model.generator(self.blur_image)
        self.save_image(image, epoch + 1)
        

    def on_train_begin(self, logs=None):
        """Create a unique path for save the images o this train session."""
        self.folder = '{path}/{datetime}.jpg'.format(
            path=self.path,
            datetime=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

        self.save_image(self.sharp_image, 'sharp')
        self.save_image(self.blur_image, 'blur')

    def save_image(self, image, name):
        """
        Transform, serialize and write image to disk.

        Args:
            image (tensor): shape [h, w, 3] dtype float32
            name (str): name for the file
        """
        # Converts to encodable uint8 type
        image = (image * 128) + 127
        image = tf.cast(image, dtype=tf.uint8)

        # Remove batch dimession from the tensor
        image = tf.squeeze(image)

        # Encodes and write image to disk
        encoded = tf.io.encode_jpeg(image)

        file_name = '{path}/{name}.jpg'.format(
            path=self.folder,
            name=name,
        )

        tf.io.write_file(file_name, encoded)