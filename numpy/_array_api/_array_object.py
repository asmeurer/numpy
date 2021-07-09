"""
Wrapper class around the ndarray object for the array API standard.

The array API standard defines some behaviors differently than ndarray, in
particular, type promotion rules are different (the standard has no
value-based casting). The standard also specifies a more limited subset of
array methods and functionalities than are implemented on ndarray. Since the
goal of the array_api namespace is to be a minimal implementation of the array
API standard, we need to define a separate wrapper class for the array_api
namespace.

The standard compliant class is only a wrapper class. It is *not* a subclass
of ndarray.
"""

from __future__ import annotations

import operator
from enum import IntEnum
from ._creation_functions import asarray
from ._dtypes import _boolean_dtypes, _integer_dtypes, _floating_dtypes

from typing import TYPE_CHECKING, Any, Optional, Tuple, Union
if TYPE_CHECKING:
    from ._typing import PyCapsule, Device, Dtype

import numpy as np

class Array:
    """
    n-d array object for the array API namespace.

    See the docstring of :py:obj:`np.ndarray <numpy.ndarray>` for more
    information.

    This is a wrapper around numpy.ndarray that restricts the usage to only
    those things that are required by the array API namespace. Note,
    attributes on this object that start with a single underscore are not part
    of the API specification and should only be used internally. This object
    should not be constructed directly. Rather, use one of the creation
    functions, such as asarray().

    """
    # Use a custom constructor instead of __init__, as manually initializing
    # this class is not supported API.
    @classmethod
    def _new(cls, x, /):
        """
        This is a private method for initializing the array API Array
        object.

        Functions outside of the array_api submodule should not use this
        method. Use one of the creation functions instead, such as
        ``asarray``.

        """
        obj = super().__new__(cls)
        # Note: The spec does not have array scalars, only shape () arrays.
        if isinstance(x, np.generic):
            # Convert the array scalar to a shape () array
            xa = np.empty((), x.dtype)
            xa[()] = x
            x = xa
        obj._array = x
        return obj

    # Prevent Array() from working
    def __new__(cls, *args, **kwargs):
        raise TypeError("The array_api Array object should not be instantiated directly. Use an array creation function, such as asarray(), instead.")

    # These functions are not required by the spec, but are implemented for
    # the sake of usability.

    def __str__(self: Array, /) -> str:
        """
        Performs the operation __str__.
        """
        return self._array.__str__().replace('array', 'Array')

    def __repr__(self: Array, /) -> str:
        """
        Performs the operation __repr__.
        """
        return self._array.__repr__().replace('array', 'Array')

    # Helper function to match the type promotion rules in the spec
    def _promote_scalar(self, scalar):
        """
        Returns a promoted version of a Python scalar appropriate for use with
        operations on self.

        This may raise an OverflowError in cases where the scalar is an
        integer that is too large to fit in a NumPy integer dtype, or
        TypeError when the scalar type is incompatible with the dtype of self.
        """
        if isinstance(scalar, bool):
            if self.dtype not in _boolean_dtypes:
                raise TypeError("Python bool scalars can only be promoted with bool arrays")
        elif isinstance(scalar, int):
            if self.dtype in _boolean_dtypes:
                raise TypeError("Python int scalars cannot be promoted with bool arrays")
        elif isinstance(scalar, float):
            if self.dtype not in _floating_dtypes:
                raise TypeError("Python float scalars can only be promoted with floating-point arrays.")
        else:
            raise TypeError("'scalar' must be a Python scalar")

        # Note: the spec only specifies integer-dtype/int promotion
        # behavior for integers within the bounds of the integer dtype.
        # Outside of those bounds we use the default NumPy behavior (either
        # cast or raise OverflowError).
        return Array._new(np.array(scalar, self.dtype))

    @staticmethod
    def _normalize_two_args(x1, x2):
        """
        Normalize inputs to two arg functions to fix type promotion rules

        NumPy deviates from the spec type promotion rules in cases where one
        argument is 0-dimensional and the other is not. For example:

        >>> import numpy as np
        >>> a = np.array([1.0], dtype=np.float32)
        >>> b = np.array(1.0, dtype=np.float64)
        >>> np.add(a, b) # The spec says this should be float64
        array([2.], dtype=float32)

        To fix this, we add a dimension to the 0-dimension array before passing it
        through. This works because a dimension would be added anyway from
        broadcasting, so the resulting shape is the same, but this prevents NumPy
        from not promoting the dtype.
        """
        if x1.shape == () and x2.shape != ():
            # The _array[None] workaround was chosen because it is relatively
            # performant. broadcast_to(x1._array, x2.shape) is much slower. We
            # could also manually type promote x2, but that is more complicated
            # and about the same performance as this.
            x1 = Array._new(x1._array[None])
        elif x2.shape == () and x1.shape != ():
            x2 = Array._new(x2._array[None])
        return (x1, x2)

    # Everything below this line is required by the spec.

    def __abs__(self: Array, /) -> Array:
        """
        Performs the operation __abs__.
        """
        res = self._array.__abs__()
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __add__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __add__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__add__(other._array)
        return self.__class__._new(res)

    def __and__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __and__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__and__(other._array)
        return self.__class__._new(res)

    def __array_namespace__(self: Array, /, *, api_version: Optional[str] = None) -> object:
        if api_version is not None:
            raise ValueError("Unrecognized array API version")
        from numpy import _array_api
        return _array_api

    def __bool__(self: Array, /) -> bool:
        """
        Performs the operation __bool__.
        """
        # Note: This is an error here.
        if self._array.shape != ():
            raise TypeError("bool is only allowed on arrays with shape ()")
        res = self._array.__bool__()
        return res

    def __dlpack__(self: Array, /, *, stream: Optional[Union[int, Any]] = None) -> PyCapsule:
        """
        Performs the operation __dlpack__.
        """
        res = self._array.__dlpack__(stream=None)
        return self.__class__._new(res)

    def __dlpack_device__(self: Array, /) -> Tuple[IntEnum, int]:
        """
        Performs the operation __dlpack_device__.
        """
        # Note: device support is required for this
        res = self._array.__dlpack_device__()
        return self.__class__._new(res)

    def __eq__(self: Array, other: Union[int, float, bool, Array], /) -> Array:
        """
        Performs the operation __eq__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__eq__(other._array)
        return self.__class__._new(res)

    def __float__(self: Array, /) -> float:
        """
        Performs the operation __float__.
        """
        # Note: This is an error here.
        if self._array.shape != ():
            raise TypeError("float is only allowed on arrays with shape ()")
        res = self._array.__float__()
        return res

    @np.errstate(all='ignore')
    def __floordiv__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __floordiv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__floordiv__(other._array)
        return self.__class__._new(res)

    def __ge__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __ge__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__ge__(other._array)
        return self.__class__._new(res)

    # Note: A large fraction of allowed indices are disallowed here (see the
    # docstring below)
    @staticmethod
    def _validate_index(key, shape):
        """
        Validate an index according to the array API.

        The array API specification only requires a subset of indices that are
        supported by NumPy. This function will reject any index that is
        allowed by NumPy but not required by the array API specification. We
        always raise ``IndexError`` on such indices (the spec does not require
        any specific behavior on them, but this makes the NumPy array API
        namespace a minimal implementation of the spec).

        This function either raises IndexError if the index ``key`` is
        invalid, or a new key to be used in place of ``key`` in indexing. It
        only raises ``IndexError`` on indices that are not already rejected by
        NumPy, as NumPy will already raise the appropriate error on such
        indices. ``shape`` may be None, in which case, only cases that are
        independent of the array shape are checked.

        The following cases are allowed by NumPy, but not specified by the array
        API specification:

        - The start and stop of a slice may not be out of bounds. In
          particular, for a slice ``i:j:k`` on an axis of size ``n``, only the
          following are allowed:

          - ``i`` or ``j`` omitted (``None``).
          - ``-n <= i <= max(0, n - 1)``.
          - For ``k > 0`` or ``k`` omitted (``None``), ``-n <= j <= n``.
          - For ``k < 0``, ``-n - 1 <= j <= max(0, n - 1)``.

        - Boolean array indices are not allowed as part of a larger tuple
          index.

        - Integer array indices are not allowed (with the exception of shape
          () arrays, which are treated the same as scalars).

        Additionally, it should be noted that indices that would return a
        scalar in NumPy will return a shape () array. Array scalars are not allowed
        in the specification, only shape () arrays. This is done in the
        ``Array._new`` constructor, not this function.

        """
        if isinstance(key, slice):
            if shape is None:
                return key
            if shape == ():
                return key
            size = shape[0]
            # Ensure invalid slice entries are passed through.
            if key.start is not None:
                try:
                    operator.index(key.start)
                except TypeError:
                    return key
                if not (-size <= key.start <= max(0, size - 1)):
                    raise IndexError("Slices with out-of-bounds start are not allowed in the array API namespace")
            if key.stop is not None:
                try:
                    operator.index(key.stop)
                except TypeError:
                    return key
                step = 1 if key.step is None else key.step
                if (step > 0 and not (-size <= key.stop <= size)
                    or step < 0 and not (-size - 1 <= key.stop <= max(0, size - 1))):
                    raise IndexError("Slices with out-of-bounds stop are not allowed in the array API namespace")
            return key

        elif isinstance(key, tuple):
            key = tuple(Array._validate_index(idx, None) for idx in key)

            for idx in key:
                if isinstance(idx, np.ndarray) and idx.dtype in _boolean_dtypes or isinstance(idx, (bool, np.bool_)):
                    if len(key) == 1:
                        return key
                    raise IndexError("Boolean array indices combined with other indices are not allowed in the array API namespace")

            if shape is None:
                return key
            n_ellipsis = key.count(...)
            if n_ellipsis > 1:
                return key
            ellipsis_i = key.index(...) if n_ellipsis else len(key)

            for idx, size in list(zip(key[:ellipsis_i], shape)) + list(zip(key[:ellipsis_i:-1], shape[:ellipsis_i:-1])):
                Array._validate_index(idx, (size,))
            return key
        elif isinstance(key, bool):
            return key
        elif isinstance(key, Array):
            if key.dtype in _integer_dtypes:
                if key.shape != ():
                    raise IndexError("Integer array indices with shape != () are not allowed in the array API namespace")
            return key._array
        elif key is Ellipsis:
            return key
        elif key is None:
            raise IndexError("newaxis indices are not allowed in the array API namespace")
        try:
            return operator.index(key)
        except TypeError:
            # Note: This also omits boolean arrays that are not already in
            # Array() form, like a list of booleans.
            raise IndexError("Only integers, slices (`:`), ellipsis (`...`), and boolean arrays are valid indices in the array API namespace")

    def __getitem__(self: Array, key: Union[int, slice, ellipsis, Tuple[Union[int, slice, ellipsis], ...], Array], /) -> Array:
        """
        Performs the operation __getitem__.
        """
        # Note: Only indices required by the spec are allowed. See the
        # docstring of _validate_index
        key = self._validate_index(key, self.shape)
        res = self._array.__getitem__(key)
        return self._new(res)

    def __gt__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __gt__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__gt__(other._array)
        return self.__class__._new(res)

    def __int__(self: Array, /) -> int:
        """
        Performs the operation __int__.
        """
        # Note: This is an error here.
        if self._array.shape != ():
            raise TypeError("int is only allowed on arrays with shape ()")
        res = self._array.__int__()
        return res

    def __invert__(self: Array, /) -> Array:
        """
        Performs the operation __invert__.
        """
        res = self._array.__invert__()
        return self.__class__._new(res)

    def __le__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __le__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__le__(other._array)
        return self.__class__._new(res)

    # Note: __len__ may end up being removed from the array API spec.
    def __len__(self, /) -> int:
        """
        Performs the operation __len__.
        """
        res = self._array.__len__()
        return self.__class__._new(res)

    def __lshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __lshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        # Note: The spec requires the return dtype of bitwise_left_shift, and
        # hence also __lshift__, to be the same as the first argument.
        # np.ndarray.__lshift__ returns a type that is the type promotion of
        # the two input types.
        res = self._array.__lshift__(other._array).astype(self.dtype)
        return self.__class__._new(res)

    def __lt__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __lt__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__lt__(other._array)
        return self.__class__._new(res)

    def __matmul__(self: Array, other: Array, /) -> Array:
        """
        Performs the operation __matmul__.
        """
        if isinstance(other, (int, float, bool)):
            # matmul is not defined for scalars, but without this, we may get
            # the wrong error message from asarray.
            other = self._promote_scalar(other)
        res = self._array.__matmul__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __mod__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __mod__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__mod__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __mul__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __mul__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__mul__(other._array)
        return self.__class__._new(res)

    def __ne__(self: Array, other: Union[int, float, bool, Array], /) -> Array:
        """
        Performs the operation __ne__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__ne__(other._array)
        return self.__class__._new(res)

    def __neg__(self: Array, /) -> Array:
        """
        Performs the operation __neg__.
        """
        res = self._array.__neg__()
        return self.__class__._new(res)

    def __or__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __or__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__or__(other._array)
        return self.__class__._new(res)

    def __pos__(self: Array, /) -> Array:
        """
        Performs the operation __pos__.
        """
        res = self._array.__pos__()
        return self.__class__._new(res)

    # PEP 484 requires int to be a subtype of float, but __pow__ should not
    # accept int.
    @np.errstate(all='ignore')
    def __pow__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __pow__.
        """
        from ._elementwise_functions import pow

        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __pow__')
        # Note: NumPy's __pow__ does not follow type promotion rules for 0-d
        # arrays, so we use pow() here instead.
        return pow(self, other)

    def __rshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __rshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        # Note: The spec requires the return dtype of bitwise_right_shift, and
        # hence also __rshift__, to be the same as the first argument.
        # np.ndarray.__rshift__ returns a type that is the type promotion of
        # the two input types.
        res = self._array.__rshift__(other._array).astype(self.dtype)
        return self.__class__._new(res)

    def __setitem__(self, key, value, /):
        """
        Performs the operation __setitem__.
        """
        # Note: Only indices required by the spec are allowed. See the
        # docstring of _validate_index
        key = self._validate_index(key, self.shape)
        res = self._array.__setitem__(key, asarray(value)._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __sub__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __sub__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__sub__(other._array)
        return self.__class__._new(res)

    # PEP 484 requires int to be a subtype of float, but __truediv__ should
    # not accept int.
    @np.errstate(all='ignore')
    def __truediv__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __truediv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __truediv__')
        self, other = self._normalize_two_args(self, other)
        res = self._array.__truediv__(other._array)
        return self.__class__._new(res)

    def __xor__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __xor__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__xor__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __iadd__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __iadd__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__iadd__(other._array)
        return self

    @np.errstate(all='ignore')
    def __radd__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __radd__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__radd__(other._array)
        return self.__class__._new(res)

    def __iand__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __iand__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__iand__(other._array)
        return self

    def __rand__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __rand__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rand__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __ifloordiv__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __ifloordiv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__ifloordiv__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rfloordiv__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __rfloordiv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rfloordiv__(other._array)
        return self.__class__._new(res)

    def __ilshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __ilshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__ilshift__(other._array)
        return self

    def __rlshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __rlshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        # Note: The spec requires the return dtype of bitwise_left_shift, and
        # hence also __lshift__, to be the same as the first argument.
        # np.ndarray.__lshift__ returns a type that is the type promotion of
        # the two input types.
        res = self._array.__rlshift__(other._array).astype(other.dtype)
        return self.__class__._new(res)

    def __imatmul__(self: Array, other: Array, /) -> Array:
        """
        Performs the operation __imatmul__.
        """
        # Note: NumPy does not implement __imatmul__.

        if isinstance(other, (int, float, bool)):
            # matmul is not defined for scalars, but without this, we may get
            # the wrong error message from asarray.
            other = self._promote_scalar(other)
        # __imatmul__ can only be allowed when it would not change the shape
        # of self.
        other_shape = other.shape
        if self.shape == () or other_shape == ():
            raise ValueError("@= requires at least one dimension")
        if len(other_shape) == 1 or other_shape[-1] != other_shape[-2]:
            raise ValueError("@= cannot change the shape of the input array")
        self._array[:] = self._array.__matmul__(other._array)
        return self

    def __rmatmul__(self: Array, other: Array, /) -> Array:
        """
        Performs the operation __rmatmul__.
        """
        if isinstance(other, (int, float, bool)):
            # matmul is not defined for scalars, but without this, we may get
            # the wrong error message from asarray.
            other = self._promote_scalar(other)
        res = self._array.__rmatmul__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __imod__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __imod__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__imod__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rmod__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __rmod__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rmod__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __imul__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __imul__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__imul__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rmul__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __rmul__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rmul__(other._array)
        return self.__class__._new(res)

    def __ior__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __ior__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__ior__(other._array)
        return self

    def __ror__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __ror__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__ror__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __ipow__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __ipow__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __pow__')
        self._array.__ipow__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rpow__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __rpow__.
        """
        from ._elementwise_functions import pow

        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __pow__')
        # Note: NumPy's __pow__ does not follow the spec type promotion rules
        # for 0-d arrays, so we use pow() here instead.
        return pow(other, self)

    def __irshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __irshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__irshift__(other._array)
        return self

    def __rrshift__(self: Array, other: Union[int, Array], /) -> Array:
        """
        Performs the operation __rrshift__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        # Note: The spec requires the return dtype of bitwise_right_shift, and
        # hence also __rshift__, to be the same as the first argument.
        # np.ndarray.__rshift__ returns a type that is the type promotion of
        # the two input types.
        res = self._array.__rrshift__(other._array).astype(other.dtype)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __isub__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __isub__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__isub__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rsub__(self: Array, other: Union[int, float, Array], /) -> Array:
        """
        Performs the operation __rsub__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rsub__(other._array)
        return self.__class__._new(res)

    @np.errstate(all='ignore')
    def __itruediv__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __itruediv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __truediv__')
        self._array.__itruediv__(other._array)
        return self

    @np.errstate(all='ignore')
    def __rtruediv__(self: Array, other: Union[float, Array], /) -> Array:
        """
        Performs the operation __rtruediv__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        if self.dtype not in _floating_dtypes or other.dtype not in _floating_dtypes:
            raise TypeError('Only floating-point dtypes are allowed in __truediv__')
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rtruediv__(other._array)
        return self.__class__._new(res)

    def __ixor__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __ixor__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self._array.__ixor__(other._array)
        return self

    def __rxor__(self: Array, other: Union[int, bool, Array], /) -> Array:
        """
        Performs the operation __rxor__.
        """
        if isinstance(other, (int, float, bool)):
            other = self._promote_scalar(other)
        self, other = self._normalize_two_args(self, other)
        res = self._array.__rxor__(other._array)
        return self.__class__._new(res)

    @property
    def dtype(self) -> Dtype:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.dtype <numpy.ndarray.dtype>`.

        See its docstring for more information.
        """
        return self._array.dtype

    @property
    def device(self) -> Device:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.device <numpy.ndarray.device>`.

        See its docstring for more information.
        """
        # Note: device support is required for this
        raise NotImplementedError("The device attribute is not yet implemented")

    @property
    def ndim(self) -> int:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.ndim <numpy.ndarray.ndim>`.

        See its docstring for more information.
        """
        return self._array.ndim

    @property
    def shape(self) -> Tuple[int, ...]:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.shape <numpy.ndarray.shape>`.

        See its docstring for more information.
        """
        return self._array.shape

    @property
    def size(self) -> int:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.size <numpy.ndarray.size>`.

        See its docstring for more information.
        """
        return self._array.size

    @property
    def T(self) -> Array:
        """
        Array API compatible wrapper for :py:meth:`np.ndaray.T <numpy.ndarray.T>`.

        See its docstring for more information.
        """
        return self._array.T