#!/usr/bin/python
# coding=utf-8

"""Defines the custom loss functions used at train time."""

import tensorflow as tf


def ragan_ls_loss(preds, real_preds):
    """
    Compute the RaGAN-LS loss of supplied prediction.

    It is a two-term binary crossentropy loss
    Author call it RaGAN-LS loss

    Args:
        preds (tf.Tensor): discriminator over real or generated batch of images
        real_preds (bool): if supplied preds comes from real images

    Returns:
        Loss of predictions compared to expectation
    """
    real_preds = tf.constant(real_preds, dtype=preds.dtype)

    # This factor allows soft/smooth labels
    # We use one sided soft labels due the ragan loss design
    soft_factor = tf.ones_like(preds)
    soft_factor += 0.1 * tf.random.uniform(
        shape=tf.shape(preds),
        minval=-1.0,
        maxval=1.0,
    )

    first_side = tf.multiply(real_preds * soft_factor, tf.square(preds - 1))
    second_side = tf.multiply((1 - real_preds) * soft_factor, tf.square(preds + 1))

    return tf.reduce_mean(first_side + second_side)


def discriminator_loss(preds, real_preds):
    """
    Compute the **TOTAL** RaGAN-LS loss of DScaleDiscrim.

    Args:
        preds (dict): discriminator output over real images
        real_preds (bool): if supplied preds comes from real images

    Returns:
        Total loss over real and fake images
    """
    loss_l = ragan_ls_loss(preds['local'], real_preds)
    loss_g = ragan_ls_loss(preds['global'], real_preds)

    return loss_l + loss_g


def generator_loss(gen_images, sharp_images, fake_pred, loss_network):
    """
    Define the cutom loss function for generator.

    It is a three-term loss:

    Lg = 0.5 * Lp + 0.006 * Lx + 0.01 * Ladv

    Lp = MSE Loss
    Lx = Perceptual Loss
    Ladv = Discriminator Loss

    Args:
        gen_images (tf.Tensor): Batch of images generated by the FPN
        sharp_images (tf.Tensor): Batch of ground truth sharp images
        fake_pred (tf.Tensor): Scalar, output of the discriminator
        loss_network (Model): Model network for perceptual loss/FRL

    Returns:
        Generator three-term loss function output
    """
    lp = tf.keras.losses.mean_squared_error(sharp_images, gen_images)
    lp = tf.reduce_mean(lp)

    lx = feature_reconstruction_loss(gen_images, sharp_images, loss_network)

    ladv = discriminator_loss(fake_pred, real_preds=True)

    return 0.5 * lp + 0.006 * lx + 0.01 * ladv


def feature_reconstruction_loss(gen_images, sharp_images, loss_network):
    """
    Compute FRL between gen image and sharp image.

    Args:
        gen_images (tf.Tensor): Batch of images generated by the FPN
        sharp_images (tf.Tensor): Batch of ground truth sharp images
        loss_network (Model): Model network for perceptual loss/FRL

    Returns:
        FR loss between generated ans sharp images
    """
    gen_output = loss_network(gen_images, training=False)
    sharp_output = loss_network(sharp_images, training=False)

    loss = gen_output - sharp_output
    loss = tf.square(loss)
    loss = tf.divide(
        loss,
        tf.cast(
            tf.math.reduce_prod(tf.shape(gen_output)[1:]),
            dtype=loss.dtype,
        ),
    )
    loss = tf.reduce_mean(loss)

    return loss