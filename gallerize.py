#!/usr/bin/env python

"""gallerize: make a simple html gallery from a directory of images.

allerize is a command line program. To run from the command line, call
gallerize.py with --help to see what options you have available.

"""

import os
import sys
import glob
import math
import urllib
import fnmatch
import tempfile
import argparse

import Image
import pyexiv2
from mako.template import Template

import thumbify


TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css" rel="stylesheet" />

        <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
        <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
        <!--[if lt IE 9]>
          <script src="//oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
          <script src="//oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
        <![endif]-->

        <style type="text/css">
            html, body {
                height: 100%;
                background-color: #333;
            }

            body {
                color: #fff;
                text-align: center;
                text-shadow: 0 1px 3px rgba(0,0,0,.5);
            }

            h1 {
                margin-bottom: 20px;
            }

            .img {
                display: inline;
            }

            img {
                margin-right: 10px;
                margin-bottom: 10px;
            }
        </style>

        <title>photostream</title>
    </head>
    <body>

        <h1>photostream</h1>

        % for image in images:
            <div class="img">
                <a href="large/${image}">
                    <img src="thumbs/${image}" alt="${image}" />
                </a>
            </div>
        % endfor

        <script type="text/javascript" src="//code.jquery.com/jquery-2.1.1.min.js"></script>
        <script type="text/javascript" src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
    </body>
</html>
"""


def ensure_directory(*parts):
    dirname = os.path.join(*parts)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--source", action="store", required=True,
                        help="The source directory to find images in.")

    parser.add_argument("--filter", action="store", default="*.jpg",
                        help="File search wildcard. *.jpg, *.png etc.")

    parser.add_argument("--destination", dest="destination", required=True,
                        help="The output directory where you want the gallery.")

    args = parser.parse_args()

    # source and destination cannot match
    if args.source == args.destination:
        raise Exception("source cannot match destination")

    # find the files to process
    selected = []
    for root, dirs, files in os.walk(args.source):
        for name in files:
            if fnmatch.fnmatch(name, args.filter):
                selected.append(os.path.join(root, name));

    # keep track of all the image names to template in
    image_names = []

    # process each file we found
    num = 0
    for file in selected:
        num += 1

        img = Image.open(file).convert("RGB")
        img = thumbify.reorient_image(img, file)

        # basic path information
        path, filename = os.path.split(file)

        # write the full size image
        fulldir = ensure_directory(args.destination, "full")
        fullpath = os.path.join(fulldir, filename)

        img.save(fullpath)

        # write the large size image
        largedir = ensure_directory(args.destination, "large")
        largepath = os.path.join(largedir, filename)

        w, h, _ = thumbify.scale_to_size(img, 1280)
        limg = img.copy()
        limg = limg.resize((w, h), Image.ANTIALIAS)
        limg.save(largepath)

        # write the medium size image
        mediumdir = ensure_directory(args.destination, "medium")
        mediumpath = os.path.join(mediumdir, filename)

        w, h, _ = thumbify.scale_to_size(img, 640)
        mimg = img.copy()
        mimg = mimg.resize((w, h), Image.ANTIALIAS)
        mimg.save(mediumpath)

        # write the small size image
        smalldir = ensure_directory(args.destination, "small")
        smallpath = os.path.join(smalldir, filename)

        w, h, _ = thumbify.scale_to_size(img, 240)
        simg = img.copy()
        simg = simg.resize((w, h), Image.ANTIALIAS)
        simg.save(smallpath)

        # write the thumbnail
        thumbdir = ensure_directory(args.destination, "thumbs")
        thumbpath = os.path.join(thumbdir, filename)

        timg = img.copy()
        timg = thumbify.square_image(timg)
        timg.thumbnail((150, 150), Image.ANTIALIAS)

        timg.save(thumbpath)

        # and collect our name
        image_names.append(filename)

    # format and write out the template
    with open(os.path.join(args.destination, "index.html"), "w") as fp:
        template = Template(TEMPLATE)
        fp.write(template.render(images=image_names))

