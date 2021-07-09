from __future__ import annotations

from ._array_object import Array

from typing import Optional, Tuple

import numpy as np

def argmax(x: Array, /, *, axis: Optional[int] = None, keepdims: bool = False) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.argmax <numpy.argmax>`.

    See its docstring for more information.
    """
    # Note: this currently fails as np.argmax does not implement keepdims
    return Array._new(np.asarray(np.argmax(x._array, axis=axis, keepdims=keepdims)))

def argmin(x: Array, /, *, axis: Optional[int] = None, keepdims: bool = False) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.argmin <numpy.argmin>`.

    See its docstring for more information.
    """
    # Note: this currently fails as np.argmin does not implement keepdims
    return Array._new(np.asarray(np.argmin(x._array, axis=axis, keepdims=keepdims)))

def nonzero(x: Array, /) -> Tuple[Array, ...]:
    """
    Array API compatible wrapper for :py:func:`np.nonzero <numpy.nonzero>`.

    See its docstring for more information.
    """
    return Array._new(np.nonzero(x._array))

def where(condition: Array, x1: Array, x2: Array, /) -> Array:
    """
    Array API compatible wrapper for :py:func:`np.where <numpy.where>`.

    See its docstring for more information.
    """
    return Array._new(np.where(condition._array, x1._array, x2._array))