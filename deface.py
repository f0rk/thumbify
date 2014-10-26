#!/usr/bin/env python

"""deface: face detection for images.

deface can be used as a library, or as a command line program.
To run from the command line, call deface.py with --help to see
what options you have available.

"""

import os
import sys
import argparse

import cv2


def detect_faces(img):
    """Converts an image to grayscale and returns the locations of any
    (suspected) faces found.

    :param img: A cv image object.

    """

    grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cascade = cv2.CascadeClassifier("/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml")

    flags = cv2.CASCADE_DO_CANNY_PRUNING | cv2.CASCADE_SCALE_IMAGE
    faces = cascade.detectMultiScale(grayscale, scaleFactor=1.1, minNeighbors=2,
                                     flags=flags, minSize=(50, 50))

    return [(x, y, w, h) for x, y, w, h in faces]


def detect_faces_file(file):
    """Given the location of an image file, it converts it to grayscale
    and returns the location of any (suspected) faces.

    :param file: The path to the image.

    """

    return detect_faces(cv2.imread(file))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="file to detect faces in")
    parser.add_argument("--draw", action="store_true",
                        help="draw rectangles on the image of the face locations")
    args = parser.parse_args()

    faces = detect_faces_file(args.file)
    if faces:
        for x, y, w, h in faces:
            print("{},{} {},{}".format(x, y, x + w, y + h))
    else:
        print("no faces detected")

