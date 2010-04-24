#!/usr/bin/python

"""thumbify: intelligently thumbnail images

thumbify can be used as a library, or as a command line program.
To run from the command line, call thumbify.py with --help to see
what options you have available.
"""

import Image

def image_entropy(img):
    """Calculate the entropy of an image.
    """
    import math
    hist = img.histogram()
    hist_size = sum(hist)
    hist = [float(h) / hist_size for h in hist]

    return -sum([p * math.log(p, 2) for p in hist if p != 0])

def square_image(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on the entropy pieces, or 
    any faces, if present.
    """
    
    x, y = img.size
    if x == y:
        return img
    
    image = face_crop(img)
    if image == None: #no/too many faces
        image = entropy_crop(img)
    
    return image
    
def entropy_crop(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on the entropy pieces.
    """
    
    x, y = img.size
    if y > x:
        while y > x:
            #slice 10px at a time until square
            slice_height = min(y - x, 10)

            bottom = img.crop((0, y - slice_height, x, y))
            top = img.crop((0, 0, x, slice_height))

            #remove the slice with the least entropy
            if image_entropy(bottom) < image_entropy(top):
                img = img.crop((0, 0, x, y - slice_height))
            else:
                img = img.crop((0, slice_height, x, y))

            x, y = img.size
    else:
         while x > y:
             #slice 10px at a time until square
             slice_width = min(x - y, 10)
             
             left = img.crop((0, 0, slice_width, y))
             right = img.crop((x - slice_width, 0, x, y))
             
             #remove the slice with the least entropy
             if image_entropy(left) < image_entropy(right):
                 img = img.crop((0, 0, x - slice_width, y))
             else:
                 img = img.crop((slice_width, 0, x, y))
                 
             x, y = img.size
                     
    return img
    
def face_crop(img):
    """If the image is not square, square it off. determine
    which pieces to cut off based on any faces, if present.
    """
    import tempfile
    import deface

    x, y = img.size
    w, h = img.size

    #face detection works better on small images
    factor = 1
    if x > 400 and y > 400:
        if x > y:
            factor = x / 400
            w = 400
            h = y / factor
        else:
            factor = y / 400
            w = x / factor
            h = 400
    
    rimg = img.copy()
    if factor != 1:
        #scaling
        rimg.thumbnail((w, h), Image.ANTIALIAS)
    
    #opencv doesn't use PIL, so we'll need a tempfile for it to operate on
    tf = tempfile.NamedTemporaryFile(suffix=".jpg")
    try:
        rimg.save(tf.name)        
    except:
        print "error saving tmp: %s" % (tf.name)
        for error in sys.exc_info():
            print "\t%s" % error
        sys.exit(-1)
    
    faces = deface.detect_faces_file(tf.name)
    
    ulx, uly, lrx, lry = x + 1, y + 1, -1, -1
    
    nfaces = 0
    if faces:
        nfaces = faces.total #hacks

    if nfaces > 0 and nfaces < 5:
        #center crop box on faces rect
        for f in faces:
            if f.x < ulx:
                ulx = f.x
            if f.y < uly:
                uly = f.y
            if f.x + f.width > lrx:
                lrx = f.x + f.width
            if f.y + f.height > lry:
                lry = f.y + f.height
                
        #translate back to full size image
        ulx = ulx * factor
        uly = uly * factor
        lrx = lrx * factor
        lry = lry * factor
        
        #get the center
        cx = ulx + (lrx - ulx) / 2
        cy = uly + (lry - uly) / 2
        
        #crop the image maximally about the given center
        wd, ht = img.size
        ulx_crop, uly_crop, lrx_crop, lry_crop = 0, 0, wd, ht
        if wd > ht:
            ulx_crop = min(wd - ht, cx - ht / 2)
            uly_crop = 0
            lrx_crop = ulx_crop + ht
            lry_crop = ht
        else:
            ulx_crop = 0
            uly_crop = min(ht - wd, cy - wd / 2)
            lrx_crop = wd
            lry_crop = uly_crop + wd
        
        #crop and return
        return img.crop((ulx_crop, uly_crop, lrx_crop, lry_crop))
    else:
        return None

if __name__ == '__main__':
    import os
    import sys
    import glob
    import fnmatch
    from optparse import OptionParser

    parser = OptionParser(usage="usage: %prog [OPTIONS]")
    
    parser.add_option("-d", "--dir", action="store", type="string", dest="directory", default="./",
                      help="The target source directory for the images to be thumbed down.")

    parser.add_option("-f", "--filter", action="store", type="string", dest="filter", default="*.jpg",
                      help="File search wildcard. *.jpg, *.png etc.")

    parser.add_option("-r", "--recursive", action="store_true", dest="recursive", default=False,
                      help="Run a recursive scan starting from the given top folder.")
    
    parser.add_option("-s", "--size", action="store", type="int", dest="size", default=150,
                      help="Size of the thumbnail image. Image will be intelligently squared")

    parser.add_option("-p", "--prefix", action="store", type="string", dest="prefix", default="",
                      help="Prefix to be added to the created thumbnail.")
    
    parser.add_option("-x", "--suffix", action="store", type="string", dest="suffix", default="",
                      help="Suffix to be added to the created thumbnail.")

    parser.add_option("-o", "--odir", action="store", type="string", dest="output_directory", default="./",
                      help="The output directory where you want to store the created thumbnails.")

    (options, args) = parser.parse_args()
    
    if len(sys.argv[1:]) == 0:
        parser.error("too few arguments (hint: try %s --help)" % (sys.argv[0]))

    #print what we're about to do...
    print ("Creating thumbnails of %s files in %s into %s\n\trecursive: %d, prefix: %s, suffix: %s, size: %d"
           % (options.filter, options.directory, options.output_directory, options.recursive, options.prefix, options.suffix, options.size))   

    files = []
    if options.recursive:
        for root, dirs, files in os.walk(options.directory):
            for name in files:
                if fnmatch.fnmatch(name, options.filter):
                    files.append(os.path.join(root, name));
    else:
        for file in glob.glob1(options.directory, options.filter):
            files.append(os.path.join(options.directory, file))

    num = 0
    for file in files:
        num += 1
        img = None
        try :
            img = Image.open(file).convert("RGB")
        except:
            print "error opening %d: %s" % (num, file)
            for error in sys.exc_info():
                print "\t%s" % error
            sys.exit(-1)

        img = square_image(img)
        img.thumbnail((options.size, options.size), Image.ANTIALIAS)
        
        (path, filename) = os.path.split(file)
        (basefilename, extension) = os.path.splitext(filename)

        #if the initial output directory is the same as the input,
        #put the thumbnails into the same subfolders as the actual images
        if (options.output_directory == options.directory):
            thumbpath = path
        else:
            thumbpath = options.output_directory
            
        thumbnail = os.path.join(thumbpath, options.prefix + basefilename + options.suffix + extension)
        print "creating %d: %s" % (num, thumbnail)
        try:
            img.save(thumbnail)        
        except:
            print "error creating %d: %s" % (num, thumbnail)
            for error in sys.exc_info():
                print "\t%s" % error
            sys.exit(-1)
    
