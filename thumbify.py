#!/usr/bin/env python

"""thumbify: intelligently thumbnail images

thumbify can be used as a library, or as a command line program.
To run from the command line, call thumbify.py with --help to see
what options you have available.

"""

import os
import glob
import math
import fnmatch
import tempfile
import argparse
import subprocess

import Image
import pyexiv2

import deface


def image_entropy(img):
    """Calculate the entropy of an image.

    :param img: The Image instance.

    """

    hist = img.histogram()
    hist_size = sum(hist)
    hist = [float(h) / hist_size for h in hist]

    return -sum([p * math.log(p, 2) for p in hist if p != 0])


def square_image(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on the entropy pieces, or
    any faces, if present.

    :param img: The Image instance.

    """

    x, y = img.size
    if x == y:
        return img

    image = face_crop(img)
    if image == None: # no/too many faces
        image = entropy_crop(img)

    return image


def entropy_crop(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on the entropy pieces.

    :param img: The Image instance.

    """

    x, y = img.size
    if y > x:
        while y > x:
            # slice 10px at a time until square
            slice_height = min(y - x, 10)

            bottom = img.crop((0, y - slice_height, x, y))
            top = img.crop((0, 0, x, slice_height))

            # remove the slice with the least entropy
            if image_entropy(bottom) < image_entropy(top):
                img = img.crop((0, 0, x, y - slice_height))
            else:
                img = img.crop((0, slice_height, x, y))

            x, y = img.size
    else:
         while x > y:
             # slice 10px at a time until square
             slice_width = min(x - y, 10)

             left = img.crop((0, 0, slice_width, y))
             right = img.crop((x - slice_width, 0, x, y))

             # remove the slice with the least entropy
             if image_entropy(left) < image_entropy(right):
                 img = img.crop((0, 0, x - slice_width, y))
             else:
                 img = img.crop((slice_width, 0, x, y))

             x, y = img.size

    return img


def scale_to_size(img, scale_size):
    """Given an image and a scale size, return the new width and height of
    the image, scaled such that the maximum dimension is the given size.

    :param img: The Image instance.
    :param scale_size: The maximum dimension.

    """

    x, y = img.size
    w, h = img.size

    factor = 1
    if x > scale_size and y > scale_size:
        if x > y:
            factor = x / float(scale_size)
            w = scale_size
            h = y / factor
        else:
            factor = y / float(scale_size)
            w = x / factor
            h = scale_size

        w = int(w)
        h = int(h)

    return w, h, factor


def face_crop(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on any faces, if present.

    :param img: The Image instance.

    """

    x, y = img.size

    # face detection works better on small images
    w, h, factor = scale_to_size(img, 600)

    rimg = img.copy()
    if factor != 1:
        # scaling
        rimg.thumbnail((w, h), Image.ANTIALIAS)

    # opencv doesn't use PIL, so we'll need a tempfile for it to operate on
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tf:
        rimg.format = "jpeg"
        rimg.save(tf.name)

        faces = deface.detect_faces_file(tf.name)

        ulx, uly, lrx, lry = x + 1, y + 1, -1, -1

        nfaces = 0
        if faces:
            nfaces = len(faces) # hacks
        if nfaces > 0 and nfaces < 5:
            # center crop box on faces rect
            for x, y, w, h in faces:

                if x < ulx:
                    ulx = x
                if y < uly:
                    uly = y
                if x + w > lrx:
                    lrx = x + w
                if y + h > lry:
                    lry = y + h

            # translate back to full size image
            ulx = ulx * factor
            uly = uly * factor
            lrx = lrx * factor
            lry = lry * factor

            # get the center
            cx = ulx + (lrx - ulx) / 2
            cy = uly + (lry - uly) / 2

            # crop the image maximally about the given center
            wd, ht = img.size
            ulx_crop, uly_crop, lrx_crop, lry_crop = 0, 0, wd, ht
            if wd > ht:
                ulx_crop = max(min(wd - ht, cx - ht / 2), 0)
                uly_crop = 0
                lrx_crop = ulx_crop + ht
                lry_crop = ht
            else:
                ulx_crop = 0
                uly_crop = max(min(ht - wd, cy - wd / 2), 0)
                lrx_crop = wd
                lry_crop = uly_crop + wd

            # crop and return
            return img.crop((int(ulx_crop), int(uly_crop), int(lrx_crop),
                             int(lry_crop)))
        else:
            return None


def reorient_image(img, file):
    """Rotate the given image to the correct orientation using the exif
    information. This method returns a copy of the image.

    :param img: The Image instance.
    :param file: The path of the original image, needed to obtain the
        extension/metadata.

    """

    _, ext = os.path.splitext(file)

    orig_meta = pyexiv2.ImageMetadata(file)
    orig_meta.read()

    with tempfile.NamedTemporaryFile(suffix=ext) as tfp:
        img.save(tfp.name)

        new_meta = pyexiv2.ImageMetadata(tfp.name)
        new_meta.read()

        orig_meta.copy(new_meta)
        new_meta.write()

        args = [
            "mogrify",
            "-auto-orient",
            tfp.name,
        ]
        process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        process.communicate()

        return Image.open(tfp.name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--source", action="store", default="./",
                        help="The source directory/file for the images to be thumbed down.")

    parser.add_argument("--filter", action="store", default="*.jpg",
                        help="File search wildcard. *.jpg, *.png etc.")

    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Run a recursive scan starting from the given top folder.")

    parser.add_argument("--size", action="store", type=int, default=150,
                        help="Size of the thumbnail image. Image will be intelligently squared")

    parser.add_argument("--prefix", action="store", default="",
                        help="Prefix to be added to the created thumbnail.")

    parser.add_argument("--suffix", action="store", default="",
                        help="Suffix to be added to the created thumbnail.")

    parser.add_argument("--destination", dest="destination", default="./",
                        help="The output directory/file where you want to store the created thumbnails.")

    args = parser.parse_args()

    # print what we're about to do...
    print("Creating thumbnail(s) of {} file(s) in '{}' into '{}'\n\t"
          "recursive: {}, prefix: '{}', suffix: '{}', size: {}"
          .format(args.filter, args.source, args.destination,
                  args.recursive, args.prefix, args.suffix, args.size))

    # find the files to process
    if os.path.isfile(args.source):
        selected = [args.source]
    else:
        selected = []
        if args.recursive:
            for root, dirs, files in os.walk(args.source):
                for name in files:
                    if fnmatch.fnmatch(name, args.filter):
                        selected.append(os.path.join(root, name));
        else:
            for file in glob.glob1(args.source, args.filter):
                selected.append(os.path.join(args.source, file))

    # process each file we found
    num = 0
    for file in selected:
        num += 1

        img = Image.open(file)
        img = reorient_image(img, file)
        img = square_image(img)
        img.thumbnail((args.size, args.size), Image.ANTIALIAS)

        path, filename = os.path.split(file)
        basefilename, extension = os.path.splitext(filename)

        # if the initial output directory is the same as the input,
        # put the thumbnails into the same subfolders as the actual images
        if args.destination == args.source:
            thumbpath = path
        else:
            thumbpath = args.destination

        if not os.path.isfile(thumbpath):
            thumbname = args.prefix + basefilename + args.suffix + extension
            thumbnail = os.path.join(thumbpath, thumbname)
        else:
            thumbnail = os.path.isfile(thumbpath)

        print("creating {}: {}".format(num, thumbnail))
        img.save(thumbnail)

