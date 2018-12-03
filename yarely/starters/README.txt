This directory contains 'starters' for Yarely.

Yarely is shipped as multiple applications and modules.

=============================================
The difference between applications & modules
=============================================

Applications are launched by a user (or perhaps a system's init, etc).  They
are provided with the path to the Yarely configuration file.

Modules are launched by Yarely.  They are not provided with the path to the
Yarely configuration file (they're expected to communicate with the host
application using ZeroMQ).

=============
Customisation
=============

A selection of environment variables can be set to customise the Yarely
deployment:

-------------------
YARELY_PYTHON32_BIN
-------------------

Path to the Python 3.2 interpreter.

A platform specific default value is used:
Darwin/Mac OS X: 'python3'
Linux: 'python3'
Windows: 'c:\python32\python.exe'

-------------
YARELY_CONFIG
-------------

The (absolute or relative) path to the Yarely configuration file (used only
by Yarely applications).

Default value: 'yarely-local/config/yarely.cfg'

For further details see the get_yarely_config() function in common.py.

-------------
YARELY_PARENT
-------------

The directory path to change into before launching (used by both applications
and modules).  This path is also appended to PYTHONPATH so that the Yarely
package can be found.  It provides a consistent environment for relative paths
to (and within) the Yarely configuration file.

A platform specific default value is used:
Darwin/Mac OS X: '$HOME/proj'
Linux: '$HOME/proj'
Windows: '$HOME\proj'

For further details see the get_yarely_parent() function in common.py

----------------------
YARELY_STARTER_VERBOSE
----------------------

If this environment variable is set (to any value), verbose diagnostic
information will be printed before the final binary is launched (used by both
applications and modules).
