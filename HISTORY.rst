=======
History
=======

0.2.0 (2019-07-16)
------------------

* Yarely now uses Qt5-based platform independent content renderers only (in yarely/qt5).
* Image: This is using QPixmap to render content. Supported image files are listed here and include png, jpg and gif.
* Video: As in the previous version of Yarely, this is using VLC (via python-vlc package) and supports any video format that is supported by VLC -- including multicast streams.
* Web: This is using Qt WebEngine and has the advantage that it doesn't need any web rendering libraries provided by the operating system. This will make it much easier to always support latest Web standards.
* In addition, this pull request also includes a number of smaller bugfixes.

0.1.0 (2018-12-01)
------------------

* First release on PyPI.
