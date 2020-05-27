# Prepare slides for a presentation on empirical priors
# output example03a.pdf

# Python 3.5+ required by pathlib
# MUST be run from top level of project directory

import sys
import numpy as np
from pathlib import Path

import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.colors import NoNorm
from matplotlib import cm
import matplotlib.pyplot as plt

import BIFS
import BIFS.bifs_util.EmpiricalScanner as EmpScnr

# Use the empirical prior to alter the raw MRI.  We'd like to get close to the true PET
MRIFILE = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\ycobigo\round3\ana_res-2019-02-21_SPM\CBF_PVC_GM\mniwCBF_PVC_GM_10933_2012-09-21.nii"
PETFILE = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\ycobigo\round3\ana_res-2019-02-21_SPM\T1\mniwSUVR_10933_2012-09-21.nii"
# Empirical Prior file
EPFILE = r"C:\Users\rdboylan\Documents\Kornak\ep1.npz"

TOPPET = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\ycobigo\round3\ana_res-2019-02-21_SPM\T1"
PETMATCH = r"^mniwSUVR_.*\.nii(\.gz)?$"
PETEXCLUDE = r"10933"

def slice(image, ix=0, frac=0.5):
    "return rotated 2D slice of 3D image"
    # rotate 90 degrees counter clockwise
    # ix and frac apply before rotation
    slice_index = np.int(np.round(frac*image.shape[ix]))
    if ix == 0:
        im_slice = image[slice_index,:,:]
    elif ix == 1:
        im_slice = image[:,slice_index,:]
    elif ix == 2:
        im_slice = image[:,:,slice_index]
    else:
        raise RuntimeError("Sorry slice index needs to be one of 0,1,2")
    return np.rot90(im_slice)

def plot_prep(image):
    "standard plot preparation for a 2D image"
    fig = Figure()
    plt.rcParams["axes.grid"] = False # turn off grid lines for images
    plt.rcParams["xtick.color"] = (1,1,1,0)
    plt.rcParams["ytick.color"] = (1,1,1,0)
    plt.imshow(image, cmap = cm.Greys_r)

def plot_post(pp):
    "standard processing after all plotting of this page done"
    pp.savefig()
    # the text just the final plt.text persisted across figures without the next line
    plt.clf()

def referenceVoxels():
    """return  sorted array of voxels from images scanned"""
    scanner = EmpScnr.EmpiricalScanner(sampleFraction=0.10, topDir=TOPPET, matchFile=PETMATCH, exclude=PETEXCLUDE)
    r = scanner.vox
    del scanner
    return r

def adjustImage(img):
    """
    Adjust the distribution of pixels in the input image.
    Returns an input image of the same size with the intensity distribution adjusted 
    to match that in some scanned files.  Roughly the n'th percentile of image brightness in img
    will be assigned the n'th percentile of the reference images.
    """
    ref = referenceVoxels()
    # argsort appears to break ties in a way that preserves the order it encounters elements
    flat = img.reshape(-1)
    ix = flat.argsort()
    # The parentheses around ref.size/img.size are essential.
    # Otherwise values wrap around
    subi = np.array(np.round(np.arange(img.size)*(ref.size/img.size)), dtype='int')
    refx = ref[subi]
    # not having much luck doing adjustments in place
    r = np.empty_like(flat)
    r[ix] = refx
    return r.reshape(img.shape)


def example03():
    """ Illustrate Use of Empirical Prior"""
    b = BIFS.bifs()
    b.load_image_file(MRIFILE)
    b.load_empirical(EPFILE)

    try:
        Path('example03b.pdf').unlink()
    except:
        # for file not found
        pass
    pp = PdfPages('example03b.pdf')

    #info on slice to display
    ix = 0
    frac = 0.5

    init_image = slice(b.init_image(), ix = ix, frac = frac)
    # make sure aliasing doesn't overwrite this
    original = init_image.copy()
    print(type(b.init_image()), b.init_image().dtype)
    print(b.init_image().max())
    plot_prep(init_image)
    plt.title("Initial MRI image")
    plot_post(pp)

    b._init_image = adjustImage(b._init_image)
    init_image = slice(b.init_image(), ix = ix, frac = frac)
    plot_prep(init_image)
    plt.title("MRI image with PET distribution")
    print("After adjustment")
    x1 = b.init_image()
    print(type(x1), x1.dtype)
    x2 = np.ravel(x1)
    print(x2.max())
    plot_post(pp)

    prior = b.prior_object()
    for scale in (0.4, 0.8, 1.0, 2.0, 4.0):
        prior.setScale(scale)
        b._invalidate_final()  # would be unnecessary in perfect world
        img = slice(b.final_image(), ix = ix, frac = frac)
        plot_prep(img)
        plt.title("MRI after Empirical Prior, scale {}".format(scale))
        plot_post(pp)
        plot_prep(img - original)
        plt.title("Delta from original MRI image")
        plot_post(pp)

    pet = BIFS.bifs()
    pet.load_image_file(PETFILE)

    init_image = slice(pet.init_image(), ix = ix, frac = frac)
    plot_prep(init_image)
    plt.title("Actual PET image")
    plot_post(pp)

    pp.close()

if __name__ == "__main__":

    example03()