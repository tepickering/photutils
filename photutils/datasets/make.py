# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module provides tools for making example datasets for examples and
tests.
"""

from collections import OrderedDict

from astropy import coordinates as coord
from astropy.convolution import discretize_model
from astropy.io import fits
from astropy.modeling import models
from astropy.table import Table
import astropy.units as u
from astropy.version import version as astropy_version
from astropy.wcs import WCS
import numpy as np

from ..psf import IntegratedGaussianPRF
from ..utils import check_random_state

__all__ = ['apply_poisson_noise', 'make_noise_image',
           'make_random_models_table', 'make_random_gaussians_table',
           'make_model_sources_image', 'make_gaussian_sources_image',
           'make_4gaussians_image', 'make_100gaussians_image',
           'make_wcs', 'make_gwcs', 'make_imagehdu',
           'make_gaussian_prf_sources_image']

__doctest_requires__ = {('make_gwcs'): ['gwcs']}


def apply_poisson_noise(data, random_state=None):
    """
    Apply Poisson noise to an array, where the value of each element in
    the input array represents the expected number of counts.

    Each pixel in the output array is generated by drawing a random
    sample from a Poisson distribution whose expectation value is given
    by the pixel value in the input array.

    Parameters
    ----------
    data : array-like
        The array on which to apply Poisson noise.  Every pixel in the
        array must have a positive value (i.e. counts).

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.

    Returns
    -------
    result : `~numpy.ndarray`
        The data array after applying Poisson noise.

    See Also
    --------
    make_noise_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils.datasets import make_4gaussians_image
        from photutils.datasets import apply_poisson_noise
        data1 = make_4gaussians_image(noise=False)
        data2 = apply_poisson_noise(data1, random_state=12345)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
        ax1.imshow(data1, origin='lower', interpolation='nearest')
        ax1.set_title('Original image')
        ax2.imshow(data2, origin='lower', interpolation='nearest')
        ax2.set_title('Original image with Poisson noise applied')
    """

    data = np.asanyarray(data)
    if np.any(data < 0):
        raise ValueError('data must not contain any negative values')

    prng = check_random_state(random_state)

    return prng.poisson(data)


def make_noise_image(shape, type='gaussian', mean=None, stddev=None,
                     random_state=None):
    """
    Make a noise image containing Gaussian or Poisson noise.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the output 2D image.

    type : {'gaussian', 'poisson'}
        The distribution used to generate the random noise:

            * ``'gaussian'``: Gaussian distributed noise.
            * ``'poisson'``: Poisson distributed noise.

    mean : float
        The mean of the random distribution.  Required for both Gaussian
        and Poisson noise.  The default is 0.

    stddev : float, optional
        The standard deviation of the Gaussian noise to add to the
        output image.  Required for Gaussian noise and ignored for
        Poisson noise (the variance of the Poisson distribution is equal
        to its mean).

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same noise parameters and
        ``random_state`` will generate the identical noise image.

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing random noise.

    See Also
    --------
    apply_poisson_noise

    Examples
    --------
    .. plot::
        :include-source:

        # make Gaussian and Poisson noise images
        from photutils.datasets import make_noise_image
        shape = (100, 100)
        image1 = make_noise_image(shape, type='gaussian', mean=0., stddev=5.)
        image2 = make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax1.set_title('Gaussian noise ($\\mu=0$, $\\sigma=5.$)')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax2.set_title('Poisson noise ($\\mu=5$)')
    """

    if mean is None:
        raise ValueError('"mean" must be input')

    prng = check_random_state(random_state)

    if type == 'gaussian':
        if stddev is None:
            raise ValueError('"stddev" must be input for Gaussian noise')
        image = prng.normal(loc=mean, scale=stddev, size=shape)
    elif type == 'poisson':
        image = prng.poisson(lam=mean, size=shape)
    else:
        raise ValueError('Invalid type: {0}. Use either "gaussian" or '
                         '"poisson".'.format(type))

    return image


def make_random_models_table(n_sources, param_ranges, random_state=None):
    """
    Make a `~astropy.table.Table` containing randomly generated
    parameters for an Astropy model to simulate a set of sources.

    Each row of the table corresponds to a source whose parameters are
    defined by the column names.  The parameters are drawn from a
    uniform distribution over the specified input ranges.

    The output table can be input into :func:`make_model_sources_image`
    to create an image containing the model sources.

    Parameters
    ----------
    n_sources : float
        The number of random model sources to generate.

    param_ranges : dict
        The lower and upper boundaries for each of the model parameters
        as a `dict` mapping the parameter name to its ``(lower, upper)``
        bounds.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.

    Returns
    -------
    table : `~astropy.table.Table`
        A table of parameters for the randomly generated sources.  Each
        row of the table corresponds to a source whose model parameters
        are defined by the column names.  The column names will be the
        keys of the dictionary ``param_ranges``.

    See Also
    --------
    make_random_gaussians_table, make_model_sources_image

    Notes
    -----
    To generate identical parameter values from separate function calls,
    ``param_ranges`` must be input as an `~collections.OrderedDict` with
    the same parameter ranges and ``random_state`` must be the same.

    Examples
    --------
    >>> from collections import OrderedDict
    >>> from photutils.datasets import make_random_models_table
    >>> n_sources = 5
    >>> param_ranges = [('amplitude', [500, 1000]),
    ...                 ('x_mean', [0, 500]),
    ...                 ('y_mean', [0, 300]),
    ...                 ('x_stddev', [1, 5]),
    ...                 ('y_stddev', [1, 5]),
    ...                 ('theta', [0, np.pi])]
    >>> param_ranges = OrderedDict(param_ranges)
    >>> sources = make_random_models_table(n_sources, param_ranges,
    ...                                    random_state=12345)
    >>> for col in sources.colnames:
    ...     sources[col].info.format = '%.8g'  # for consistent table output
    >>> print(sources)
    amplitude   x_mean    y_mean   x_stddev  y_stddev   theta
    --------- --------- --------- --------- --------- ----------
    964.80805 297.77235 224.31444 3.6256447 3.5699013  2.2923859
    658.18778 482.25726 288.39202 4.2392502 3.8698145  3.1227889
    591.95941 326.58855 2.5164894 4.4887037  2.870396  2.1264615
    602.28014 374.45332 31.933313 4.8585904 2.3023387  2.4844422
    783.86251 326.78494 89.611114 3.8947414 2.7585784 0.53694298
    """

    prng = check_random_state(random_state)

    sources = Table()
    for param_name, (lower, upper) in param_ranges.items():
        # Generate a column for every item in param_ranges, even if it
        # is not in the model (e.g. flux).  However, such columns will
        # be ignored when rendering the image.
        sources[param_name] = prng.uniform(lower, upper, n_sources)

    return sources


def make_random_gaussians_table(n_sources, param_ranges, random_state=None):
    """
    Make a `~astropy.table.Table` containing randomly generated
    parameters for 2D Gaussian sources.

    Each row of the table corresponds to a Gaussian source whose
    parameters are defined by the column names.  The parameters are
    drawn from a uniform distribution over the specified input ranges.

    The output table can be input into
    :func:`make_gaussian_sources_image` to create an image containing
    the 2D Gaussian sources.

    Parameters
    ----------
    n_sources : float
        The number of random Gaussian sources to generate.

    param_ranges : dict
        The lower and upper boundaries for each of the
        `~astropy.modeling.functional_models.Gaussian2D` parameters as a
        `dict` mapping the parameter name to its ``(lower, upper)``
        bounds.  The dictionary keys must be valid
        `~astropy.modeling.functional_models.Gaussian2D` parameter names
        or ``'flux'``.  If ``'flux'`` is specified, but not
        ``'amplitude'`` then the 2D Gaussian amplitudes will be
        calculated and placed in the output table.  If both ``'flux'``
        and ``'amplitude'`` are specified, then ``'flux'`` will be
        ignored.  Model parameters not defined in ``param_ranges`` will
        be set to the default value.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.

    Returns
    -------
    table : `~astropy.table.Table`
        A table of parameters for the randomly generated Gaussian
        sources.  Each row of the table corresponds to a Gaussian source
        whose parameters are defined by the column names.

    See Also
    --------
    make_random_models_table, make_gaussian_sources_image

    Notes
    -----
    To generate identical parameter values from separate function calls,
    ``param_ranges`` must be input as an `~collections.OrderedDict` with
    the same parameter ranges and ``random_state`` must be the same.

    Examples
    --------
    >>> from collections import OrderedDict
    >>> from photutils.datasets import make_random_gaussians_table
    >>> n_sources = 5
    >>> param_ranges = [('amplitude', [500, 1000]),
    ...                 ('x_mean', [0, 500]),
    ...                 ('y_mean', [0, 300]),
    ...                 ('x_stddev', [1, 5]),
    ...                 ('y_stddev', [1, 5]),
    ...                 ('theta', [0, np.pi])]
    >>> param_ranges = OrderedDict(param_ranges)
    >>> sources = make_random_gaussians_table(n_sources, param_ranges,
    ...                                       random_state=12345)
    >>> for col in sources.colnames:
    ...     sources[col].info.format = '%.8g'  # for consistent table output
    >>> print(sources)
    amplitude   x_mean    y_mean   x_stddev  y_stddev   theta
    --------- --------- --------- --------- --------- ----------
    964.80805 297.77235 224.31444 3.6256447 3.5699013  2.2923859
    658.18778 482.25726 288.39202 4.2392502 3.8698145  3.1227889
    591.95941 326.58855 2.5164894 4.4887037  2.870396  2.1264615
    602.28014 374.45332 31.933313 4.8585904 2.3023387  2.4844422
    783.86251 326.78494 89.611114 3.8947414 2.7585784 0.53694298

    To specifying the flux range instead of the amplitude range:

    >>> param_ranges = [('flux', [500, 1000]),
    ...                 ('x_mean', [0, 500]),
    ...                 ('y_mean', [0, 300]),
    ...                 ('x_stddev', [1, 5]),
    ...                 ('y_stddev', [1, 5]),
    ...                 ('theta', [0, np.pi])]
    >>> param_ranges = OrderedDict(param_ranges)
    >>> sources = make_random_gaussians_table(n_sources, param_ranges,
    ...                                       random_state=12345)
    >>> for col in sources.colnames:
    ...     sources[col].info.format = '%.8g'  # for consistent table output
    >>> print(sources)
       flux     x_mean    y_mean   x_stddev  y_stddev   theta    amplitude
    --------- --------- --------- --------- --------- ---------- ---------
    964.80805 297.77235 224.31444 3.6256447 3.5699013  2.2923859 11.863685
    658.18778 482.25726 288.39202 4.2392502 3.8698145  3.1227889 6.3854388
    591.95941 326.58855 2.5164894 4.4887037  2.870396  2.1264615 7.3122209
    602.28014 374.45332 31.933313 4.8585904 2.3023387  2.4844422 8.5691781
    783.86251 326.78494 89.611114 3.8947414 2.7585784 0.53694298 11.611707

    Note that in this case the output table contains both a flux and
    amplitude column.  The flux column will be ignored when generating
    an image of the models using :func:`make_gaussian_sources_image`.
    """

    sources = make_random_models_table(n_sources, param_ranges,
                                       random_state=random_state)

    # convert Gaussian2D flux to amplitude
    if 'flux' in param_ranges and 'amplitude' not in param_ranges:
        model = models.Gaussian2D(x_stddev=1, y_stddev=1)

        if 'x_stddev' in sources.colnames:
            xstd = sources['x_stddev']
        else:
            xstd = model.x_stddev.value  # default
        if 'y_stddev' in sources.colnames:
            ystd = sources['y_stddev']
        else:
            ystd = model.y_stddev.value  # default

        sources = sources.copy()
        sources['amplitude'] = sources['flux'] / (2. * np.pi * xstd * ystd)

    return sources


def make_model_sources_image(shape, model, source_table, oversample=1):
    """
    Make an image containing sources generated from a user-specified
    model.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the output 2D image.

    model : 2D astropy.modeling.models object
        The model to be used for rendering the sources.

    source_table : `~astropy.table.Table`
        Table of parameters for the sources.  Each row of the table
        corresponds to a source whose model parameters are defined by
        the column names, which must match the model parameter names.
        Column names that do not match model parameters will be ignored.
        Model parameters not defined in the table will be set to the
        ``model`` default value.

    oversample : float, optional
        The sampling factor used to discretize the models on a pixel
        grid.  If the value is 1.0 (the default), then the models will
        be discretized by taking the value at the center of the pixel
        bin.  Note that this method will not preserve the total flux of
        very small sources.  Otherwise, the models will be discretized
        by taking the average over an oversampled grid.  The pixels will
        be oversampled by the ``oversample`` factor.

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing model sources.

    See Also
    --------
    make_random_models_table, make_gaussian_sources_image

    Examples
    --------
    .. plot::
        :include-source:

        from collections import OrderedDict
        from astropy.modeling.models import Moffat2D
        from photutils.datasets import (make_random_models_table,
                                        make_model_sources_image)

        model = Moffat2D()
        n_sources = 10
        shape = (100, 100)
        param_ranges = [('amplitude', [100, 200]),
                        ('x_0', [0, shape[1]]),
                        ('y_0', [0, shape[0]]),
                        ('gamma', [5, 10]),
                        ('alpha', [1, 2])]
        param_ranges = OrderedDict(param_ranges)
        sources = make_random_models_table(n_sources, param_ranges,
                                           random_state=12345)

        data = make_model_sources_image(shape, model, sources)
        plt.imshow(data)
    """

    image = np.zeros(shape, dtype=np.float64)
    yidx, xidx = np.indices(shape)

    params_to_set = []
    for param in source_table.colnames:
        if param in model.param_names:
            params_to_set.append(param)

    # Save the initial parameter values so we can set them back when
    # done with the loop.  It's best not to copy a model, because some
    # models (e.g. PSF models) may have substantial amounts of data in
    # them.
    init_params = {param: getattr(model, param) for param in params_to_set}

    try:
        for source in source_table:
            for param in params_to_set:
                setattr(model, param, source[param])

            if oversample == 1:
                image += model(xidx, yidx)
            else:
                image += discretize_model(model, (0, shape[1]),
                                          (0, shape[0]), mode='oversample',
                                          factor=oversample)
    finally:
        for param, value in init_params.items():
            setattr(model, param, value)

    return image


def make_gaussian_sources_image(shape, source_table, oversample=1):
    """
    Make an image containing 2D Gaussian sources.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the output 2D image.

    source_table : `~astropy.table.Table`
        Table of parameters for the Gaussian sources.  Each row of the
        table corresponds to a Gaussian source whose parameters are
        defined by the column names.  With the exception of ``'flux'``,
        column names that do not match model parameters will be ignored
        (flux will be converted to amplitude).  If both ``'flux'`` and
        ``'amplitude'`` are present, then ``'flux'`` will be ignored.
        Model parameters not defined in the table will be set to the
        default value.

    oversample : float, optional
        The sampling factor used to discretize the models on a pixel
        grid.  If the value is 1.0 (the default), then the models will
        be discretized by taking the value at the center of the pixel
        bin.  Note that this method will not preserve the total flux of
        very small sources.  Otherwise, the models will be discretized
        by taking the average over an oversampled grid.  The pixels will
        be oversampled by the ``oversample`` factor.

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing 2D Gaussian sources.

    See Also
    --------
    make_model_sources_image, make_random_gaussians_table

    Examples
    --------
    .. plot::
        :include-source:

        # make a table of Gaussian sources
        from astropy.table import Table
        table = Table()
        table['amplitude'] = [50, 70, 150, 210]
        table['x_mean'] = [160, 25, 150, 90]
        table['y_mean'] = [70, 40, 25, 60]
        table['x_stddev'] = [15.2, 5.1, 3., 8.1]
        table['y_stddev'] = [2.6, 2.5, 3., 4.7]
        table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.

        # make an image of the sources without noise, with Gaussian
        # noise, and with Poisson noise
        from photutils.datasets import make_gaussian_sources_image
        from photutils.datasets import make_noise_image
        shape = (100, 200)
        image1 = make_gaussian_sources_image(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=5.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax1.set_title('Original image')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax2.set_title('Original image with added Gaussian noise'
                      ' ($\\mu = 5, \\sigma = 5$)')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
        ax3.set_title('Original image with added Poisson noise ($\\mu = 5$)')
    """

    model = models.Gaussian2D(x_stddev=1, y_stddev=1)

    if 'x_stddev' in source_table.colnames:
        xstd = source_table['x_stddev']
    else:
        xstd = model.x_stddev.value  # default
    if 'y_stddev' in source_table.colnames:
        ystd = source_table['y_stddev']
    else:
        ystd = model.y_stddev.value  # default

    colnames = source_table.colnames
    if 'flux' in colnames and 'amplitude' not in colnames:
        source_table = source_table.copy()
        source_table['amplitude'] = (source_table['flux'] /
                                     (2. * np.pi * xstd * ystd))

    return make_model_sources_image(shape, model, source_table,
                                    oversample=oversample)


def make_gaussian_prf_sources_image(shape, source_table):
    """
    Make an image containing 2D Gaussian sources.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the output 2D image.

    source_table : `~astropy.table.Table`
        Table of parameters for the Gaussian sources.  Each row of the
        table corresponds to a Gaussian source whose parameters are
        defined by the column names.  With the exception of ``'flux'``,
        column names that do not match model parameters will be ignored
        (flux will be converted to amplitude).  If both ``'flux'`` and
        ``'amplitude'`` are present, then ``'flux'`` will be ignored.
        Model parameters not defined in the table will be set to the
        default value.

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing 2D Gaussian sources.

    See Also
    --------
    make_model_sources_image, make_random_gaussians_table

    Examples
    --------
    .. plot::
        :include-source:

        # make a table of Gaussian sources
        from astropy.table import Table
        table = Table()
        table['amplitude'] = [50, 70, 150, 210]
        table['x_0'] = [160, 25, 150, 90]
        table['y_0'] = [70, 40, 25, 60]
        table['sigma'] = [15.2, 5.1, 3., 8.1]

        # make an image of the sources without noise, with Gaussian
        # noise, and with Poisson noise
        from photutils.datasets import make_gaussian_prf_sources_image
        from photutils.datasets import make_noise_image
        shape = (100, 200)
        image1 = make_gaussian_prf_sources_image(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=5.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax1.set_title('Original image')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax2.set_title('Original image with added Gaussian noise'
                      ' ($\\mu = 5, \\sigma = 5$)')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
        ax3.set_title('Original image with added Poisson noise ($\\mu = 5$)')
    """

    model = IntegratedGaussianPRF(sigma=1)

    if 'sigma' in source_table.colnames:
        sigma = source_table['sigma']
    else:
        sigma = model.sigma.value  # default

    colnames = source_table.colnames
    if 'flux' not in colnames and 'amplitude' in colnames:
        source_table = source_table.copy()
        source_table['flux'] = (source_table['amplitude'] *
                                (2. * np.pi * sigma * sigma))

    return make_model_sources_image(shape, model, source_table,
                                    oversample=1)


def make_4gaussians_image(noise=True):
    """
    Make an example image containing four 2D Gaussians plus a constant
    background.

    The background has a mean of 5.

    If ``noise`` is `True`, then Gaussian noise with a mean of 0 and a
    standard deviation of 5 is added to the output image.

    Parameters
    ----------
    noise : bool, optional
        Whether to include noise in the output image (default is
        `True`).

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing four 2D Gaussian sources.

    See Also
    --------
    make_100gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_4gaussians_image()
        plt.imshow(image, origin='lower', interpolation='nearest')
    """

    table = Table()
    table['amplitude'] = [50, 70, 150, 210]
    table['x_mean'] = [160, 25, 150, 90]
    table['y_mean'] = [70, 40, 25, 60]
    table['x_stddev'] = [15.2, 5.1, 3., 8.1]
    table['y_stddev'] = [2.6, 2.5, 3., 4.7]
    table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.

    shape = (100, 200)
    data = make_gaussian_sources_image(shape, table) + 5.

    if noise:
        data += make_noise_image(shape, type='gaussian', mean=0.,
                                 stddev=5., random_state=12345)

    return data


def make_100gaussians_image(noise=True):
    """
    Make an example image containing 100 2D Gaussians plus a constant
    background.

    The background has a mean of 5.

    If ``noise`` is `True`, then Gaussian noise with a mean of 0 and a
    standard deviation of 2 is added to the output image.

    Parameters
    ----------
    noise : bool, optional
        Whether to include noise in the output image (default is
        `True`).

    Returns
    -------
    image : 2D `~numpy.ndarray`
        Image containing 100 2D Gaussian sources.

    See Also
    --------
    make_4gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_100gaussians_image()
        plt.imshow(image, origin='lower', interpolation='nearest')
    """

    n_sources = 100
    flux_range = [500, 1000]
    xmean_range = [0, 500]
    ymean_range = [0, 300]
    xstddev_range = [1, 5]
    ystddev_range = [1, 5]
    params = OrderedDict([('flux', flux_range),
                          ('x_mean', xmean_range),
                          ('y_mean', ymean_range),
                          ('x_stddev', xstddev_range),
                          ('y_stddev', ystddev_range),
                          ('theta', [0, 2*np.pi])])

    sources = make_random_gaussians_table(n_sources, params,
                                          random_state=12345)

    shape = (300, 500)
    data = make_gaussian_sources_image(shape, sources) + 5.

    if noise:
        data += make_noise_image(shape, type='gaussian', mean=0.,
                                 stddev=2., random_state=12345)

    return data


def make_wcs(shape, galactic=False):
    """
    Create a simple celestial `~astropy.wcs.WCS` object in either the
    ICRS or Galactic coordinate frame.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the 2D array to be used with the output
        `~astropy.wcs.WCS` object.

    galactic : bool, optional
        If `True`, then the output WCS will be in the Galactic
        coordinate frame.  If `False` (default), then the output WCS
        will be in the ICRS coordinate frame.

    Returns
    -------
    wcs : `astropy.wcs.WCS` object
        The world coordinate system (WCS) transformation.

    See Also
    --------
    make_gwcs, make_imagehdu

    Notes
    -----
    The `make_gwcs` function returns an equivalent WCS transformation to
    this one, but in a `gwcs.wcs.WCS` object.

    Examples
    --------
    >>> from photutils.datasets import make_wcs
    >>> shape = (100, 100)
    >>> wcs = make_wcs(shape)
    >>> print(wcs.wcs.crpix)  # doctest: +FLOAT_CMP
    [50. 50.]
    >>> print(wcs.wcs.crval)  # doctest: +FLOAT_CMP
    [197.8925      -1.36555556]
    """

    wcs = WCS(naxis=2)
    rho = np.pi / 3.
    scale = 0.1 / 3600.  # 0.1 arcsec/pixel in deg/pix

    if astropy_version < '3.1':
        wcs._naxis1 = shape[1]  # nx
        wcs._naxis2 = shape[0]  # ny
    else:
        wcs.pixel_shape = shape

    wcs.wcs.crpix = [shape[1] / 2, shape[0] / 2]  # 1-indexed (x, y)
    wcs.wcs.crval = [197.8925, -1.36555556]
    wcs.wcs.cunit = ['deg', 'deg']
    wcs.wcs.cd = [[-scale * np.cos(rho), scale * np.sin(rho)],
                  [scale * np.sin(rho), scale * np.cos(rho)]]
    if not galactic:
        wcs.wcs.radesys = 'ICRS'
        wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    else:
        wcs.wcs.ctype = ['GLON-CAR', 'GLAT-CAR']

    return wcs


def make_gwcs(shape, galactic=False):
    """
    Create a simple celestial gWCS object in the ICRS coordinate frame.

    This function requires the `gwcs
    <https://github.com/spacetelescope/gwcs>`_ package.

    Parameters
    ----------
    shape : 2-tuple of int
        The shape of the 2D array to be used with the output
        `~astropy.wcs.WCS` object.

    galactic : bool, optional
        If `True`, then the output WCS will be in the Galactic
        coordinate frame.  If `False` (default), then the output WCS
        will be in the ICRS coordinate frame.

    Returns
    -------
    wcs : `gwcs.wcs.WCS` object
        The generalized world coordinate system (WCS) transformation.

    See Also
    --------
    make_wcs, make_imagehdu

    Notes
    -----
    The `make_wcs` function returns an equivalent WCS transformation to
    this one, but in an `astropy.wcs.WCS` object.

    Examples
    --------
    >>> from photutils.datasets import make_gwcs
    >>> shape = (100, 100)
    >>> gwcs = make_gwcs(shape)
    >>> print(gwcs)
      From      Transform
    -------- ----------------
    detector linear_transform
        icrs             None
    """

    from gwcs import wcs as gwcs_wcs
    from gwcs import coordinate_frames as cf

    rho = np.pi / 3.
    scale = 0.1 / 3600.  # 0.1 arcsec/pixel in deg/pix

    shift_by_crpix = (models.Shift((-shape[1] / 2) + 1) &
                      models.Shift((-shape[0] / 2) + 1))

    cd_matrix = np.array([[-scale * np.cos(rho), scale * np.sin(rho)],
                          [scale * np.sin(rho), scale * np.cos(rho)]])

    rotation = models.AffineTransformation2D(cd_matrix, translation=[0, 0])
    rotation.inverse = models.AffineTransformation2D(
        np.linalg.inv(cd_matrix), translation=[0, 0])

    tan = models.Pix2Sky_TAN()
    celestial_rotation = models.RotateNative2Celestial(197.8925, -1.36555556,
                                                       180.0)

    det2sky = shift_by_crpix | rotation | tan | celestial_rotation
    det2sky.name = 'linear_transform'

    detector_frame = cf.Frame2D(name='detector', axes_names=('x', 'y'),
                                unit=(u.pix, u.pix))

    if galactic:
        sky_frame = cf.CelestialFrame(reference_frame=coord.Galactic(),
                                      name='galactic', unit=(u.deg, u.deg))
    else:
        sky_frame = cf.CelestialFrame(reference_frame=coord.ICRS(),
                                      name='icrs', unit=(u.deg, u.deg))

    pipeline = [(detector_frame, det2sky), (sky_frame, None)]

    return gwcs_wcs.WCS(pipeline)


def make_imagehdu(data, wcs=None):
    """
    Create a FITS `~astropy.io.fits.ImageHDU` containing the input 2D
    image.

    Parameters
    ----------
    data : 2D array-like
        The input 2D data.

    wcs : `~astropy.wcs.WCS`, optional
        The world coordinate system (WCS) transformation to include in
        the output FITS header.

    Returns
    -------
    image_hdu : `~astropy.io.fits.ImageHDU`
        The FITS `~astropy.io.fits.ImageHDU`.

    See Also
    --------
    make_wcs

    Examples
    --------
    >>> from photutils.datasets import make_imagehdu, make_wcs
    >>> shape = (100, 100)
    >>> data = np.ones(shape)
    >>> wcs = make_wcs(shape)
    >>> hdu = make_imagehdu(data, wcs=wcs)
    >>> print(hdu.data.shape)
    (100, 100)
    """

    data = np.asanyarray(data)
    if data.ndim != 2:
        raise ValueError('data must be a 2D array')

    if wcs is not None:
        header = wcs.to_header()
    else:
        header = None

    return fits.ImageHDU(data, header=header)
