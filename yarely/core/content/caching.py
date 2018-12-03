# Standard library import
import contextlib
import hashlib
import logging
import os
import shutil
import queue
import threading
from urllib.request import URLError, urlopen

# Local (Yarely) imports
from yarely.core.content.helpers import (
    get_initial_args, UnsupportedMimeTypeError
)


CACHE_URLOPEN_DEFAULT_CHUNK = 16 * 1024
CACHE_HASH_GEN_DEFAULT_CHUNK = 32 * 1024
DEFAULT_NUMBER_OF_THREADS = 5
RETRY_FAILED_TIMEOUT = 5*60  # seconds
DOWNLOAD_SUFFIX = ".download"
log = logging.getLogger(__name__)


class Cache(object):
    """ Yarely caching module. """
    def __init__(self, cache_dir, url_open_timeout=1):
        """ We expect cache_dir to be an absolute path!
        url_open_timeout in seconds.
        """
        self.cache_dir  = cache_dir
        self.url_open_timeout = url_open_timeout

    def _get_file_download_path(self, content_item):
        file_path = self._get_file_path(content_item)
        download_path = file_path + DOWNLOAD_SUFFIX
        return download_path

    @staticmethod
    def _get_file_hashes(file_path, chunk_size=CACHE_HASH_GEN_DEFAULT_CHUNK):
        """ Generates md5 and sha1 file hash for file path - chunk by chunk and
        should thus support big files.

        :param file_path: full path to file.
        :return: list of hashes.
        """
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)

        return [sha1_hash.hexdigest(), md5_hash.hexdigest()]

    @staticmethod
    def _get_file_name(content_item):
        """ Creates an sha1 hash from URI to be used as the filename. """

        # We have to keep the file extension for the video renderer.
        # If uri is an URL then file_extension might be an empty string (but
        # file_name will still consist of the whole uri). This shouldn't matter
        # as in this case as we will just append nothing to the hashed URI.
        uri = str(content_item)
        file_name, file_extension = os.path.splitext(uri)
        uri_hashed = hashlib.sha1(file_name.encode()).hexdigest()
        output_file_name = "{hashed_file_name}{extension}".format(
            hashed_file_name=uri_hashed, extension=file_extension
        )
        return output_file_name

    def _get_file_path(self, content_item):
        """ Creates full file path for items to be cached. """
        return os.path.join(self.cache_dir, self._get_file_name(content_item))

    def _save_file(self, content_item):
        """ Download the file from URI and save it into cache_path.
        Files are downloaded with a downlaod suffix and moved into their final
        directory when the download has completed.
        """

        cache_path = self._get_file_path(content_item)
        download_path = self._get_file_download_path(content_item)
        uri = str(content_item)

        log.debug("Trying to cache: {uri} into: {cache_path}".format(
            uri=str(content_item), cache_path=cache_path
        ))

        try:
            with contextlib.closing(
                urlopen(uri, timeout=self.url_open_timeout)
            ) as url_handler:
                self._write_file_from_url(url_handler, download_path)

        except URLError as e:
            log.error("Error while opening URL: {}".format(e))
            raise CachingURLError()

        # Remove the download suffix as the download has finished here.
        shutil.move(download_path, cache_path)

        return cache_path

    @staticmethod
    def _write_file_from_url(
            url_handler, path, chunk_size=CACHE_URLOPEN_DEFAULT_CHUNK
    ):
        """ Writes chunk by chunk from an urlopen object into local path. This
        can handle large downloads.
        """
        try:
            with open(path, 'wb') as f:
                # Keep requesting chunk after chunk until we don't get anything
                # back anymore.
                while True:
                    chunk = url_handler.read(chunk_size)

                    if not chunk:
                        break

                    f.write(chunk)
        except IOError as e:
            log.error(
                "Error while trying to open file for caching {}".format(e)
            )
            raise CachingIOError()

    def cache_file(self, content_item, refresh=False):
        """ Cache a file into the cache directory if it doesn't exist yet. If
        caching was successful, it will return the local path to the cached
        file.

        It will raise CachingURLError if the file couldn't be found at URI or
        the connection timed out.

        It will raise CachingIOError if the file couldn't be written into the
        filesystem, e.g. when the cache directory is read-only or full.
        """
        cached = self.file_cached(content_item)

        # Stop here if the file already exists and we don't want to refresh it
        if not refresh and cached:
            return cached

        return self._save_file(content_item)

    def file_cached(self, content_item, strict=True):
        """ Returns path to file if URI was already cached, None otherwise.

        If strict is set to True, we will compare both file names and file
        hashes. Please note that this may take longer for big files such as
        videos. To make it faster, set strict to False to just check if the
        cached file exists locally.
        """
        cache_path = self._get_file_path(content_item)

        # first let us check if the file exists at all.
        if not os.path.isfile(cache_path):
            return None

        # If not strict, then we just return the file name as by know we know
        # that the file exists.
        if not strict:
            log.debug(
                "File {} exists, not strict so returning cache path.".format(
                    str(content_item)
                )
            )
            return cache_path

        # If we want to be strict, we have to compare the actual file hashes.

        # Now we know it exists, so let us check its hash
        # For this we will check both, md5 and sha1
        hashes = self._get_file_hashes(cache_path)

        # Fixme:
        # we add str(content_item), i.e. the URI to the item, to hashes list in
        # case content descriptor set does not contain a hash for this item.
        # This may not be an ideal solution but prevents Yarely to keep caching
        # an item just because the hash is missing.
        hashes.append(str(content_item))

        content_file = content_item.get_files()[0]

        if content_file.get_identity() in hashes:
            log.debug("File {} is cached".format(str(content_item)))
            return cache_path

        log.debug(
            "Hashes don't match! Local: {local} VS. Server: {server}".format(
                local=content_file.get_identity(), server=repr(hashes)
            )
        )

        # If md5 or sha1 don't match, we delete the file and return None.
        try:
            log.debug("Deleting old file: {}".format(cache_path))
            os.remove(cache_path)
        except OSError as e:
            log.error("OS Error deleting {} - {}".format(cache_path, e))

        log.debug("File NOT cached (or old) {uri} - {cache_path}".format(
            uri=str(content_item), cache_path=cache_path
        ))

        return None

    def file_downloading(self, content_item):
        """ Returns true if the file to be cached is currently downloading. """
        download_path = self._get_file_download_path(content_item)
        return os.path.isfile(download_path)

    @staticmethod
    def needs_to_be_cached(content_item):
        """ Checks if a file needs to be or can be cached. """

        if content_item.get_type() == 'inline':
            return False

        # Get the content type of the ContentItem object
        content_type = content_item.get_content_type()

        try:
            args = get_initial_args(content_type)
        except UnsupportedMimeTypeError:
            return False

        return 'precache' in args and args['precache']


class CachingFailedError(Exception):
    pass


class CachingIOError(CachingFailedError):
    pass


class CachingURLError(CachingFailedError):
    pass


class CacheManager(object):
    """ Starts and manages cache listener threads that wait on the cache queue
    for new items to be cached.
    """

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_queue = queue.Queue()
        self.caching_threads = set()

    def cache_file(self, content_item):
        """ Cache content item (adds it to the queue) """
        self.cache_queue.put(content_item)

    def start(self, number_of_threads=DEFAULT_NUMBER_OF_THREADS):
        """ Start N threads that are waiting on the cache queue. """

        for i in range(number_of_threads):
            tmp_t_name = "caching-listener-thread-{}".format(i)
            log.debug("Starting {}".format(tmp_t_name))
            tmp_caching_thread = CacheListener(self, tmp_t_name)
            tmp_caching_thread.start()


class CacheListener(threading.Thread):
    """ One cache listener instance that grabs items from the queue of the
    cache manager and initiates caching for this item.
    """

    def __init__(self, cache_mgr, thread_name):
        super().__init__(name=thread_name)
        self.cache_mgr = cache_mgr
        self.cache = Cache(self.cache_mgr.cache_dir)

    def _cache_queue(self):
        return self.cache_mgr.cache_queue

    def run(self):
        """ Start listening for new caching requests. """

        log.debug("{} listening for cache queue.".format(self.name))

        # TODO: grow and shrink the pool size (i.e. if the queue is Empty
        # shrink the set of listener threads, if it's N times bigger than the
        # set of listeners then grow the listeners.

        while True:
            try:
                # Block on queue only for 1 second so that we can break out.
                content_item = self._cache_queue().get(True, 1)
                uri_to_be_cached = str(content_item)
            except queue.Empty:
                continue

            # Stop here if the file is currently downloading.
            if self.cache.file_downloading(content_item):
                log.debug("{file} already downloading. Skipping now.".format(
                    file=uri_to_be_cached
                ))
                continue

            # Skip this if the file was already cached, e.g. if a process
            # started caching in the meantime.
            if self.cache.file_cached(content_item):
                continue

            # Skip the file if it doesn't need to be cached.
            if not self.cache.needs_to_be_cached(content_item):
                continue

            try:
                log.debug("Trying to cache: {}".format(uri_to_be_cached))
                self.cache.cache_file(content_item)
            except CachingURLError:
                log.error("Can't cache: {}".format(str(content_item)))

                # If we failed to cache an item, start a timer for re-adding it
                # to the queue after some time.
                threading.Timer(
                    interval=RETRY_FAILED_TIMEOUT,
                    function=lambda: self._cache_queue().put(content_item)
                ).start()
