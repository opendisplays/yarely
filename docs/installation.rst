.. highlight:: shell

============
Installation
============


Stable release
--------------

To install Yarely, run this command in your terminal:

.. code-block:: console

    $ pip install yarely

This is the preferred method to install Yarely, as it will always install the most recent stable release. 

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for Yarely can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/opendisplays/yarely

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/opendisplays/yarely/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/opendisplays/yarely
.. _tarball: https://github.com/opendisplays/yarely/tarball/master

Keeping Yarely up to date
-------------------------

The suggested way for keeping Yarely up to date is to download the latest stable from PyPI on a regular basis.

If you wish to update from a Yarely fork that, for example, is hosted on GitHub, you could add the following line into a shell script:

.. code-block:: console

    $ pdnet$ pip3 install --upgrade -e git+https://github.com/opendisplays/yarely.git@master#egg=yarely --src ~/proj

In this case, we install Yarely from the masters branch into the `proj` directory in the user's home directory.
