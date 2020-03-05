# Post-conference output of selected data files
# presentation04.py
# OUTPUT example04.npz

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

import nibabel

import BIFS
import BIFS.bifs_util.EmpiricalScanner as EmpScnr

# results go here
OUTPUTFILE = "example04.npz"
PERSIST = {}  # keys are <str> names, values are np arrays

# whether to output titles
HEADINGS=False

# whether to produce pdf
MAKEPDF=False

# Use the empirical prior to alter the raw MRI.  We'd like to get close to the true PET
MRIFILE = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\ycobigo\round3\ana_res-2019-02-21_SPM\CBF_PVC_GM\mniwCBF_PVC_GM_10933_2012-09-21.nii"
PETFILE = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\ycobigo\round3\ana_res-2019-02-21_SPM\T1\mniwSUVR_10933_2012-09-21.nii"
ATLASFILE = r"C:\Users\rdboylan\Documents\Kornak\ExternalData\RosenProject\Desikan.nii"

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
    if not MAKEPDF:
        return
    fig = Figure()
    plt.rcParams["axes.grid"] = False # turn off grid lines for images
    plt.rcParams["xtick.color"] = (1,1,1,0)
    plt.rcParams["ytick.color"] = (1,1,1,0)
    plt.imshow(image, cmap = cm.Greys_r)

def plot_post(pp):
    "standard processing after all plotting of this page done"
    if not MAKEPDF:
        return
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

    Earlier work revealed interference patterns outside the active area.
    This uses an atlas to blank the boundary.
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
    r = r.reshape(img.shape)
    # and blank the area outside the brain
    mp = nibabel.load(ATLASFILE).get_fdata()
    r[mp == 0] = 0.0
    return r, mp

def example04():
    """ Illustrate Use of Empirical Prior"""
    b = BIFS.bifs()
    b.load_image_file(MRIFILE)
    b.load_empirical(EPFILE)

    if MAKEPDF:
        try:
            Path(OUTPUTFILE).unlink()
        except:
            pass
        pp = PdfPages(OUTPUTFILE)
    else:
        print("There will be no PDF output.  {} has data.".format(OUTPUTFILE))
        pp = None

    #info on slice to display
    ix = 2
    frac = 0.5

    original = b.init_image()  # 3d, so can use mask
    init_image = slice(b.init_image(), ix = ix, frac = frac)
    PERSIST["MRIORIGINAL"] = b.init_image().copy()
    PERSIST["MRIK"] = b.k_image().copy()
    PERSIST["MRIMOD"] = b.mod_image().copy()
    print(type(b.init_image()), b.init_image().dtype)
    print(b.init_image().max())
    plot_prep(init_image)
    if HEADINGS:
        plt.title("Initial MRI image")
    plot_post(pp)

    b._init_image, mp = adjustImage(b._init_image)
    PERSIST["MRIADJUST"] = b._init_image.copy()
    print(b._init_image.shape, mp.shape)
    mp[mp>0] = 1
    PERSIST["MASK"] = mp.copy()
    mp_slice = slice(mp, ix = ix, frac = frac)
    plot_prep(mp_slice)
    if HEADINGS:
        plt.title("Atlas Boundary")
    plot_post(pp)

    original[mp==0.0] = 0.0
    # original in not really original any more!
    masked = slice(original, ix = ix, frac = frac)
    plot_prep(masked)
    if HEADINGS:
        plt.title("Masked MRI image")
    plot_post(pp)

    init_image = slice(b.init_image(), ix = ix, frac = frac)

    plot_prep(init_image)
    baseline = init_image.copy()
    PERSIST["MRIBASELINE"] = baseline
    if HEADINGS:
        plt.title("MRI image with PET distribution and blanked margins")
    print("After adjustment")
    x1 = b.init_image()
    print(type(x1), x1.dtype)
    x2 = np.ravel(x1)
    print(x2.max())
    plot_post(pp)

    prior = b.prior_object()
    for scale in (.001, .01, .1, 0.4, 0.8, 1.0, 2.0, 4.0, 40.0, 100.0):
        prior.setScale(scale)
        b._invalidate_final()  # would be unnecessary in perfect world
        img = slice(b.final_image(), ix = ix, frac = frac)
        plot_prep(img)
        if HEADINGS:
            plt.title("MRI after Empirical Prior, scale {}".format(scale))
        plot_post(pp)
        delta = img-baseline
        PERSIST["MRIEP{}".format(scale)] = delta.copy()
        plot_prep(delta)
        if HEADINGS:
            plt.title("Delta from rescaled, cropped MRI image")
        plot_post(pp)

    pet = BIFS.bifs()
    pet.load_image_file(PETFILE)

    PERSIST["PETORIGINAL"] = pet.init_image().copy()
    PERSIST["PETK"] = pet.k_image()
    PERSIST["PETMOD"] = pet.mod_image()

    init_image = slice(pet.init_image(), ix = ix, frac = frac)
    plot_prep(init_image)
    if HEADINGS:
        plt.title("Actual PET image")
    plot_post(pp)

    masked = pet.init_image().copy()
    masked[mp == 0.0] = 0.0
    img = slice(masked, ix=ix, frac=frac)
    plot_prep(img)
    if HEADINGS:
        plt.title("Masked PET image")
    plot_post(pp)

    if MAKEPDF:
        pp.close()

    np.savez_compressed(OUTPUTFILE, **PERSIST)

def flippy():
    """
    Try to figure out why atlas is not working.
    Output example03-atlas.pdf
    """
    b = BIFS.bifs()
    b.load_image_file(MRIFILE)

    try:
        Path('example03-atlas.pdf').unlink()
    except:
        pass
    pp = PdfPages('example03-atlas.pdf')

    #info on slice to display
    ix = 0
    frac = 0.5

    im3 = b.init_image()
    im3[im3>3.5] = 3.5
    flip_one(im3, "MRI, limited range", pp)

    mp = nibabel.load(ATLASFILE).get_fdata()
    #mp[mp>0] = 1.0
    flip_one(mp, "ATLAS", pp)
    pp.close()

def flip_one(d, title, pp):
    """ Display various slices of an image
    d  3D image data
    title  title for plots
    pp  PdfPages object to plot to
    """
    for ix in range(3):
        for frac in (0.2, 0.5, 0.75):
            s = slice(d, ix = ix, frac = frac)
            plot_prep(s)
            plt.title("{} ix={}, frac={}".format(title, ix, frac))
            plot_post(pp)

if __name__ == "__main__":

    example04()