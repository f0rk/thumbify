#!/usr/bin/python

import sys, os
from opencv.cv import *
from opencv.highgui import *
 
def detect_faces(image):
    """Converts an image to grayscale and returns the locations of any
    (suspected) faces found.
    """
    grayscale = cvCreateImage(cvSize(image.width, image.height), 8, 1)
    cvCvtColor(image, grayscale, CV_BGR2GRAY)
 
    storage = cvCreateMemStorage(0)
    cvClearMemStorage(storage)
    cvEqualizeHist(grayscale, grayscale)
    cascade = cvLoadHaarClassifierCascade(
        '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
        cvSize(1,1))
    faces = cvHaarDetectObjects(grayscale, cascade, storage, 1.2, 2,
                             CV_HAAR_DO_CANNY_PRUNING, cvSize(50,50))
    return faces

def detect_faces_file(file):
    """Given the location of an image file, it converts it to grayscale
    and returns the location of any (suspected) faces.
    """
    return detect_faces(cvLoadImage(file))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "usage: %s FILE\n" % (sys.argv[0])
        print "error: too few arguments"
        sys.exit(-1)
    if len(sys.argv) > 2:
        print "usage: %s FILE\n" % (sys.argv[0])
        print "error: too many arguments"
        sys.exit(-1)
    
    faces = detect_faces_file(sys.argv[1])
    if faces:
        for f in faces:
            print("%d,%d %d,%d" % (f.x, f.y, f.x + f.width, f.y + f.height))
    else:
        print "no faces detected"
