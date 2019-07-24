import json
import urllib.request
from uuid import UUID


class APIWrapper(object):
    """
    API wrapper to handle all requests and interaction with the analytics API.
    """

    default_options = {
        "HOST": "scc-pheme-ana.lancaster.ac.uk",
        "PORT": 80,
        "PATH": "/analytics/report",
        "METHOD": "POST"
    }

    def __init__(self, options=None):
        if options is None:
            self.default_options = options

    def _get_send_analytics_url(self):
        host = self.default_options['HOST']
        port = str(self.default_options['PORT'])
        path = self.default_options['PATH']
        if port is not None and port != 80:
            host += ":" + str(port)
        url = "http://" + host + path
        return url

    def _set_default_handler(self, obj):
        """
        Default handler for serializing objects.
        Based on http://stackoverflow.com/questions/22281059/
        """
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError

    def send_data(self, data):
        """
        Send data to the analyitcs server. Data should be a dictionary.
        Takes care of serialization of data etc.
        """
        data_to_send = json.dumps(data, default=self._set_default_handler)
        binary_data = data_to_send.encode(encoding='utf_8', errors='strict')
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(
            self._get_send_analytics_url(), binary_data, headers
        )
        try:
            f = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        except urllib.error.URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        else:
            response = f.read()
            f.close()
            return response
