+++++++++++++++++++++++++++++++++++++++++++++++
Convert macros to functions in the Python C API
+++++++++++++++++++++++++++++++++++++++++++++++

::

    PEP: xxx
    Title: Convert macros to static inline functions
    Author: Victor Stinner <vstinner@python.org>
    Status: Draft
    Type: Standards Track
    Content-Type: text/x-rst
    Created: 19-Oct-2021
    Python-Version: 3.11


Abstract
========

Convert macros to static inline functions or regular functions.

Remove the return value of macros having a return value, whereas they should
not, to prevent misusing the C API and to detect bugs in C extensions.

Some function arguments are still casted to ``PyObject*`` to prevent emitting
new compiler warnings.


Rationale
=========

The use of macros may have unintended adverse effects that are hard to avoid,
even for the experienced C developers. Some issues have been known for
years, while others have been discovered recently in Python. Working around
macro pitfalls makes the macro coder harder to read and to maintain.

Converting macros to static inline functions and regular functions has multiple
advantages:

* By design, functions don't have macro pitfalls.
* Arguments type and return type are well defined.
* Debuggers and profilers can retrieve the name of inlined functions.
* Debuggers can put breakpoints on inlined functions.
* Variables have a well defined scope.
* Code is usually easier to read and maintain than similar macro code.
  Functions don't need workaround for macro pitfalls:

  * Adding parentheses around arguments.
  * Using line continuation characters if the function is written on multiple
    lines.
  * Using ``do { ... } while (0)`` to write multiple statements.


Macro Pitfalls
==============

The `GCC documentation
<https://gcc.gnu.org/onlinedocs/cpp/Macro-Pitfalls.html>`_ lists several common
macro pitfalls:

- Misnesting;
- Operator precedence problems;
- Swallowing the semicolon;
- Duplication of side effects;
- Self-referential macros;
- Argument prescan;
- Newlines in arguments.


Macros arguments type and return type are undefined
---------------------------------------------------

Many macros cast their arguments to ``PyObject*`` each time the argument is
used. It makes the code less readable.

The return type of a macro is not defined. The macro code must be read to guess
what is the return type.


Macros are hard to read
-----------------------

Working around macro pitfalls requires to:

* Add parentheses around arguments
* Add ``do { ... } while (0)`` if there are multiple statements.
* Add commas to execute multiple expressions.

All these workarounds make the macro code harder to read and to maintain.

Use macros in macros
--------------------

Writing a macro using ``#ifdef`` or using other macros can require working
around preprocessor limitations which imply writing code harder to read.

Macro having a return value whereas it should not
-------------------------------------------------

If a macro is implemented as an expression, it has a return value. In some
cases, the macro must not have a return value and can be misued in third party
C extensions: see `bpo-30459 <https://bugs.python.org/issue30459>`_.

It is not easy to notice such issue while writing or reviewing a macro code.


Performance and inlining
========================

Static inline functions is a feature added to C99. In 2021, C compilers can
inline them and have efficient heuristics to decide if a function should be
inlined or not.

When a C compiler decides to not inline, there is likely a good reason. For
example, inlining would reuse a register which require to save/restore the
register value on the stack and so increase the stack memory usage or be less
efficient.


Debug mode
----------

When Python is built in debug mode, most compiler optimizations are disabled.
For example, Visual Studio disables inlining. Benchmarks must not be run on a
Python debug build, only on release build: using LTO and PGO is recommended for
reliable benchmarks. PGO helps the compiler to decide if function should be
inlined or not.


Force inlining
--------------

If a developer is convinced to know better machine code than C compiler, which
is very unlikely, it is still possible to mark the function with the
``Py_ALWAYS_INLINE`` macro. This macro uses ``__attribute__((always_inline))``
with GCC and Clang, and ``__forceinline`` with MSC.

So far, previous attempts to use ``Py_ALWAYS_INLINE`` didn't show any benefit
and were abandoned. See for example: `bpo-45094
<https://bugs.python.org/issue45094>`_: "Consider using ``__forceinline`` and
``__attribute__((always_inline))`` on static inline functions (``Py_INCREF``,
``Py_TYPE``) for debug builds".

When the ``Py_INCREF()`` macro was converted to a static inline functions in 2018
(`commit <https://github.com/python/cpython/commit/2aaf0c12041bcaadd7f2cc5a54450eefd7a6ff12>`__),
it was decided not to force inlining. The machine code was analyzed with
multiple C compilers and compiler options: ``Py_INCREF()`` was always inlined
without having to force inlining. The only case where it was not inlined was
debug builds, but this is acceptable for a debug build. See discussion in the
`bpo-35059 <https://bugs.python.org/issue35059>`_: "Convert Py_INCREF() and
PyObject_INIT() to inlined functions".


Prevent inlining
----------------

On the other side, the ``Py_NO_INLINE`` macro can be used to prevent inlining.
It is useful to reduce the stack memory usage, it is especially useful on
LTO+PGO builds which heavily inlines code: see `bpo-33720
<https://bugs.python.org/issue33720>`_. This macro uses ``__attribute__
((noinline))`` with GCC and Clang, and ``__declspec(noinline)`` with MSC.


Convert macros and static inline functions to regular functions
---------------------------------------------------------------

There are projects embedding Python or using Python which cannot use macros and
static inline functions. For example, projects using programming languages
other than C and C++. There are also projects written in C which make the
deliberate choice of only getting ``libpython`` symbols (functions and
variables).

Converting macros and static inline functions to regular functions make these
functions accessible to these projects.


Specification
=============

Convert macros to static inline functions
-----------------------------------------

Most macros should be converted to static inline functions to prevent `macro
pitfalls`_.

The following macros should not be converted:

* Empty macros. Example: ``#define Py_HAVE_CONDVAR``.
* Macros only defining a number, even if a constant with a well defined type
  can better. Example: ``#define METH_VARARGS 0x0001``.
* Compatibility layer for different C compilers, C language extensions, or
  recent C features.
  Example: ``#define Py_ALWAYS_INLINE __attribute__((always_inline))``.


Convert static inline functions to regular functions
----------------------------------------------------

Converting static inline functions to regular functions give access to these
functions for projects which cannot use macros and static inline functions.

The performance impact of such conversion should be measured with benchmarks.
If there is a significant slowdown, there should be a good reason to do the
conversion. One reason can be hiding some implementation details.

Using static inline functions in the internal C API is fine: the internal C API
exposes implemenation details by design and should not be used outside Python.

Cast to PyObject*
-----------------

To prevent emitting new compiler warnings, a macro is used to cast some
function arguments to ``PyObject*``, so the converted functions still accept
pointers to other structures which inherit from ``PyObject``
(ex: ``PyTupleObject``).

For example, the ``Py_TYPE(obj)`` macro casts its ``obj`` argument to
``PyObject*``.

Remove the return value
-----------------------

Macros having a return value, whereas they should not, are converted to
static inline functions or regular functions using the ``void`` return type (no
return value) to prevent misusing the C API and to detect bugs in C extensions.


Backwards Compatibility
=======================

Converting macros having a return value, whereas they should not, to functions
using the ``void`` return type is an incompatible change made on purpose: see
the `Remove the return value`_ section.


Rejected Ideas
==============

Keep macros, but fix some macro issues
--------------------------------------

The `Macro having a return value whereas it should not`_ issue can be fixed by
casting the macro result to ``void``. For example, the ``PyList_SET_ITEM()``
macro was already fixed like that.

Macros are always "inlined" with any C compiler.

The duplication of side effects can be worked around in the caller of the
macro.

People using macros should be considered "consenting adults". People who feel
unsafe with macros should simply not use them.

Example of macros hard to read
==============================

_Py_NewReference()
------------------

Example showing the usage of an ``#ifdef`` inside a macro.

Python 3.7 macro (simplified code)::

    #ifdef COUNT_ALLOCS
    #  define _Py_INC_TPALLOCS(OP) inc_count(Py_TYPE(OP))
    #  define _Py_COUNT_ALLOCS_COMMA  ,
    #else
    #  define _Py_INC_TPALLOCS(OP)
    #  define _Py_COUNT_ALLOCS_COMMA
    #endif /* COUNT_ALLOCS */

    #define _Py_NewReference(op) (                          \
        _Py_INC_TPALLOCS(op) _Py_COUNT_ALLOCS_COMMA         \
        Py_REFCNT(op) = 1)

Python 3.8 function (simplified code)::

    static inline void _Py_NewReference(PyObject *op)
    {
        _Py_INC_TPALLOCS(op);
        Py_REFCNT(op) = 1;
    }

PyObject_INIT()
---------------

Example showing the usage of commas in a macro.

Python 3.7 macro::

    #define PyObject_INIT(op, typeobj) \
        ( Py_TYPE(op) = (typeobj), _Py_NewReference((PyObject *)(op)), (op) )

Python 3.8 function (simplified code)::

    static inline PyObject*
    _PyObject_INIT(PyObject *op, PyTypeObject *typeobj)
    {
        Py_TYPE(op) = typeobj;
        _Py_NewReference(op);
        return op;
    }

    #define PyObject_INIT(op, typeobj) \
        _PyObject_INIT(_PyObject_CAST(op), (typeobj))

The function doesn't need the line continuation character. It has an explicit
``"return op;"`` rather than a surprising ``", (op)"`` at the end of the macro.
It uses one short statement per line, rather than a single long line. Inside
the function, the *op* argument has a well defined type: ``PyObject*``.


Discussions
===========

* `bpo-45490 <https://bugs.python.org/issue45490>`_:
  [meta][C API] Avoid C macro pitfalls and usage of static inline functions
  (October 2021).
* `What to do with unsafe macros
  <https://discuss.python.org/t/what-to-do-with-unsafe-macros/7771>`_
  (March 2021).
* `bpo-43502 <https://bugs.python.org/issue43502>`_: [C-API] Convert obvious
  unsafe macros to static inline functions (March 2021).


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
