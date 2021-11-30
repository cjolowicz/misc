::

    PEP: xxx
    Title: Disallow using macros as l-value
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Content-Type: text/x-rst
    Created: 30-Oct-2021
    Python-Version: 3.11


Abstract
========

Incompatible C API change disallowing using macros as l-value to allow
evolving CPython internals and to ease the C API implementation on other
Python implementation.

In practice, the majority of projects impacted by these incompatible
changes should only have to make two changes:

* Replace ``Py_TYPE(obj) = new_type;``
  with ``Py_SET_TYPE(obj, new_type);``.
* Replace ``Py_SIZE(obj) = new_size;``
  with ``Py_SET_SIZE(obj, new_size);``.


Rationale
=========

Using a macro as a l-value
--------------------------

In the Python C API, some functions are implemented as macro because
writing a macro is simpler than writing a regular function. If a macro
exposes directly a struture member, it is technically possible to use
this macro to not only get the structure member but also set it.

Example with the Python 3.10 ``Py_TYPE()`` macro::

    #define Py_TYPE(ob) (((PyObject *)(ob))->ob_type)

This macro can be used as a **r-value** to **get** an object type::

    type = Py_TYPE(object);

It can also be used as **l-value** to **set** an object type::

    Py_TYPE(object) = new_type;

It is also possible to set an object reference count and an object size
using ``Py_REFCNT()`` and ``Py_SIZE()`` macros.

Setting directly an object attribute relies on the current exact CPython
implementation. Implementing this feature in other Python
implementations can make their C API implementation less efficient.

CPython nogil fork
------------------

Sam Gross forked Python 3.8 to remove the GIL: the `nogil branch
<https://github.com/colesbury/nogil/>`_. This fork has no
``PyObject.ob_refcnt`` member, but a more elaborated implementation for
reference counting, and so the ``Py_REFCNT(obj) = new_refcnt;`` code
fails with a compiler error.

Merging the nogil fork into the upstream CPython main branch requires
first to fix this C API compatibility issue. It is a concrete example of
a Python optimization blocked indirectly by the C API.

This issue was already fixed in Python 3.10: the ``Py_REFCNT()`` macro
has been already modified to disallow using it as a l-value.

HPy project
-----------

The `HPy project <https://hpyproject.org/>`_ is a brand new C API for
Python using only handles and function calls: handles are opaque,
structure members cannot be accessed directly,and pointers cannot be
dereferenced.

Disallowing the usage of macros as l-value helps the migration of
existing C extensions to HPy by reducing differences between the C API
and the HPy API.

PyPy cpyext module
------------------

In PyPy, when a Python object is accessed by the Python C API, the PyPy
``cpyext`` module has to convert PyPy object to a CPython object. While
PyPy objects are designed to be efficient with the PyPy JIT compiler,
CPython objects are less efficient and increase the memory usage.

This PEP alone is not enough to get rid of the CPython objects in the
PyPy ``cpyext`` module, but it is a step towards this long term goal.
PyPy already supports HPy which is a better solution in the long term.


Specification
=============

Disallow using the following macros as l-value:

PyObject and PyVarObject macros
-------------------------------

* ``Py_TYPE()``: ``Py_SET_TYPE()`` must be used instead
* ``Py_SIZE()``: ``Py_SET_SIZE()`` must be used instead

The ``Py_SET_TYPE()`` function must only be used to define statically a
type. At runtime, setting an object type must be done by setting its
``__class__`` attribute. Moreover, defining types as heap types is now
recommended.

"GET" macros
------------

* ``PyByteArray_GET_SIZE()``
* ``PyBytes_GET_SIZE()``
* ``PyCFunction_GET_CLASS()``
* ``PyCFunction_GET_FLAGS()``
* ``PyCFunction_GET_FUNCTION()``
* ``PyCFunction_GET_SELF()``
* ``PyCell_GET()``
* ``PyCode_GetNumFree()``
* ``PyDescr_NAME()``
* ``PyDescr_TYPE()``
* ``PyDict_GET_SIZE()``
* ``PyFunction_GET_ANNOTATIONS()``
* ``PyFunction_GET_CLOSURE()``
* ``PyFunction_GET_CODE()``
* ``PyFunction_GET_DEFAULTS()``
* ``PyFunction_GET_GLOBALS()``
* ``PyFunction_GET_KW_DEFAULTS()``
* ``PyFunction_GET_MODULE()``
* ``PyHeapType_GET_MEMBERS()``
* ``PyInstanceMethod_GET_FUNCTION()``
* ``PyList_GET_SIZE()``
* ``PyMemoryView_GET_BASE()``
* ``PyMemoryView_GET_BUFFER()``
* ``PyMethod_GET_FUNCTION()``
* ``PyMethod_GET_SELF()``
* ``PySet_GET_SIZE()``
* ``PyTuple_GET_SIZE()``
* ``PyUnicode_GET_DATA_SIZE()``
* ``PyUnicode_GET_LENGTH()``
* ``PyUnicode_GET_LENGTH()``
* ``PyUnicode_GET_SIZE()``
* ``PyWeakref_GET_OBJECT()``

"AS" macros
-----------

* ``PyByteArray_AS_STRING()``
* ``PyBytes_AS_STRING()``
* ``PyFloat_AS_DOUBLE()``
* ``PyUnicode_AS_DATA()``
* ``PyUnicode_AS_UNICODE()``

PyUnicode macros
----------------

* ``PyUnicode_1BYTE_DATA()``
* ``PyUnicode_2BYTE_DATA()``
* ``PyUnicode_4BYTE_DATA()``
* ``PyUnicode_DATA()``
* ``PyUnicode_IS_ASCII()``
* ``PyUnicode_IS_COMPACT()``
* ``PyUnicode_IS_READY()``
* ``PyUnicode_KIND()``
* ``PyUnicode_READ()``
* ``PyUnicode_READ_CHAR()``

PyDateTime "GET" macros
-----------------------

* ``PyDateTime_DATE_GET_FOLD()``
* ``PyDateTime_DATE_GET_HOUR()``
* ``PyDateTime_DATE_GET_MICROSECOND()``
* ``PyDateTime_DATE_GET_MINUTE()``
* ``PyDateTime_DATE_GET_SECOND()``
* ``PyDateTime_DATE_GET_TZINFO()``
* ``PyDateTime_DELTA_GET_DAYS()``
* ``PyDateTime_DELTA_GET_MICROSECONDS()``
* ``PyDateTime_DELTA_GET_SECONDS()``
* ``PyDateTime_GET_DAY()``
* ``PyDateTime_GET_MONTH()``
* ``PyDateTime_GET_YEAR()``
* ``PyDateTime_TIME_GET_FOLD()``
* ``PyDateTime_TIME_GET_HOUR()``
* ``PyDateTime_TIME_GET_MICROSECOND()``
* ``PyDateTime_TIME_GET_MINUTE()``
* ``PyDateTime_TIME_GET_SECOND()``
* ``PyDateTime_TIME_GET_TZINFO()``

PyTuple_GET_ITEM() and PyList_GET_ITEM()
----------------------------------------

The ``PyTuple_GET_ITEM()`` and ``PyList_GET_ITEM()`` macros are left
unchanged.

The code pattern ``&PyTuple_GET_ITEM(tuple, 0)`` and
``&PyList_GET_ITEM(list, 0)`` is still commonly used to get access to
the inner ``PyObject**`` array.

Changing these macros would require to add a new API to get access to
the inner array which is out of the scope of this PEP.


Backwards Compatibility
=======================

The proposed C API changes are backward incompatible on purpose.  In
practice, only a minority of third party projects are affected (16
projects are known to be broken) and `most of them have already been
updated for these changes
<https://bugs.python.org/issue39573#msg401378>`__ (12 on 16).

Most projects are broken by ``Py_TYPE()`` and ``Py_SIZE()`` changes.
These two macros have been converted to static inline macro in Python
3.10 alpha versions, but the change had to be reverted since it broke
too many projects. In the meanwhile, many projects, like Cython, have
been prepared for this change by using ``Py_SET_TYPE()`` and
``Py_SET_SIZE()``. For example, projects using Cython only have to
regenerate their outdated generated C code to become compatible.

The `pythoncapi_compat project
<https://github.com/pythoncapi/pythoncapi_compat>`_ can be used to get
Python 3.9 ``Py_SET_REFCNT()``, ``Py_SET_TYPE()`` and ``Py_SET_SIZE()``
functions on Python 3.8 and older.

For the "GET" functions like ``PyDict_GET_SIZE()``, no project in the PyPI
top 5000 projects use these functions as l-value.

The ``PyFloat_AS_DOUBLE()`` function is not used as a l-value in the
PyPI top 5000 projects.

The ``PyBytes_AS_STRING()`` and ``PyByteArray_AS_STRING()`` are used as
l-value but only to modify string characters, not to override the
``PyBytesObject.ob_sval`` or ``PyByteArrayObject.ob_start`` member.
For example, Cython uses the following code which remains valid::

    PyByteArray_AS_STRING(string)[i] = (char) v;

This change does not follow the PEP 387 deprecation process. There is no
known way to emit a deprecation warning when a macro is used as a
l-value, but not when it's used differently (ex: r-value).


Rejected Idea: Leave the macros as they are
===========================================

The documentation of each function can discourage developers to use
macros to modify Python objects.

If these is a need to make an assignment, a setter function can be added
and the macro documentation can require to use the setter function. For
example, a ``Py_SET_TYPE()`` function has been added to Python 3.9 and
the ``Py_TYPE()`` documentation now requires to use the
``Py_SET_TYPE()`` function to set an object type.

If developers use macros as l-value, it's their responsibility when
their code breaks, not the Python responsibility. We are operating under
the consenting adults principle: we expect users of the Python C API to
use it as documented and expect them to take care of the fallout, if
things break when they don't.

This idea was rejected because only few developers read the
documentation, and only a minority is tracking changes of the Python C
API documentation. The majority of developers are only using CPython and
so are not aware of compatibility issues with other Python
implementations.

Moreover, continuing to allow using macros as l-values does not solve
issues of the nogil, PyPy and HPy projects.


Macros already modified
=======================

The following C API macros have already been modified to disallow using
them as l-value:

* ``PyCell_SET()``
* ``PyList_SET_ITEM()``
* ``PyTuple_SET_ITEM()``
* ``Py_REFCNT()`` (Python 3.10): ``Py_SET_REFCNT()`` must be used
* ``_PyGCHead_SET_FINALIZED()``
* ``_PyGCHead_SET_NEXT()``
* ``asdl_seq_GET()``
* ``asdl_seq_GET_UNTYPED()``
* ``asdl_seq_LEN()``
* ``asdl_seq_SET()``
* ``asdl_seq_SET_UNTYPED()``

For example, ``PyList_SET_ITEM(list, 0, item) < 0`` now fails with a
compiler error as expected.


References
==========

* `Python C API: Add functions to access PyObject
  <https://vstinner.github.io/c-api-abstract-pyobject.html>`_ (October
  2021) article by Victor Stinner
* `[C API] Disallow using PyFloat_AS_DOUBLE() as l-value
  <https://bugs.python.org/issue45476>`_
  (October 2021)
* `[capi-sig] Py_TYPE() and Py_SIZE() become static inline functions
  <https://mail.python.org/archives/list/capi-sig@python.org/thread/WGRLTHTHC32DQTACPPX36TPR2GLJAFRB/>`_
  (September 2021)
* `[C API] Avoid accessing PyObject and PyVarObject members directly: add Py_SET_TYPE() and Py_IS_TYPE(), disallow Py_TYPE(obj)=type
  <https://bugs.python.org/issue39573>`__ (February 2020)
* `bpo-30459: PyList_SET_ITEM  could be safer
  <https://bugs.python.org/issue30459>`_ (May 2017)


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
