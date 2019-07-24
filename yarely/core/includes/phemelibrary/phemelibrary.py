import configparser
import copy
import os
import threading
from urllib.parse import urlparse
import uuid

from .APIWrapper import APIWrapper
from . import IAexceptions


# SOME CONSTANTS
CONFIG_FILENAME_DEFAULT = ".analytics_config"  # Make it a hidden file.
CONFIG_SECTION_DEFAULT = "PhemeAnalytics"
CONFIG_SECTION_FALLBACK = "IxionAnalytics"
API_SERVER_CONFIG_SECTION = "APIServer"


class PhemeAnalytics(object):
    """
    Pheme Analytics package can be included in any Python application to push
    custom data for analytics purposes to Pheme.

    When initializing, the following OPTIONAL parameters can be provided:
    client_uuid: unique ID (e.g. user id). If not set, we generate a random ID.
    application_uuid: unique application ID.
    api_wrapper: provide your own API wrapper class.
    """

    _UMP_general = {
        "v": 1.1,       # protocol version
        "tid": None,    # tracking id
        "aip": None,    # anonymised IP of sender
        "qt": None,     # que time in millisec from event occured to event sent
        "z": None,      # random number to avoid browser caching
        "cid": None,    # client uuid
        "ts": None,     # timestamp of when event occured
    }

    _UMP_traffic_sources = {
        'dr': None,    # document referrer (url to host)
        "dn": None,    # campaign name
        "cs": None,    # campaign source
        "cm": None,    # campaign medium
        "ck": None,    # campaign keyword
        "cc": None,    # campaign content
        "ci": None,    # campaign id
    }

    _UMP_system_info = {
        "sr": None,    # screen resolution
        "vp": None,    # viewable area
        "de": "utf-8", # encoding
        "sd": None,    # screen colours
        "ul": "en_GB", # user language
        #"je": None,   # Java enabled
        #"fl": None,   # Fash version
    }

    _UMP_content_information = {
        "dl": None,      # full URL to content
        "dh": None,      # hostname
        "dp": None,      # path to content without
        "dt": None,      # document title
        "cd": None,      # content description
        "linkid": None,  # ID of clicked DOM element
        "md5": None,      # MD5 hash of displayed file (if content is not URL)
        "sha1": None     # SHA1 hash of displayed file (if content is not URL)
    }

    _UMP_application_tracking = {
        "an": None,    # App name
        "av": None,    # App version
    }

    _UMP_event_tracking = {
        "ec": None,  # event category
        "ea": None,  # event action
        "ev": None,  # event value
        "el": None,  # event label
    }

    _UMP_passersby_tracking = {
        "v_uuid": None,   # Unique ID of the passers by or person
        "ug": None,       # Gender of the passers by
        "ua": None,       # Age of the passers by
        "um": None,       # Mood of the passers by
    }

    _UMP_d_proximity_tracking = {
        "pd": None,    # Distance to display
        "pm": None,    # Metric used to specify distance
        "pi": None,    # Type of interaction or proximity area
        "dv": None,    # Diarection of view
        "px": None,    # x coordinate of passers-by
        "py": None,    # y coordinate of passers-by
        "pt": None,    # Time spent in proximity area
    }

    _UMP_d_interaction = {
        "it": None,    # Interaction type, e.g. "touch", or "move"
        "ix": None,    # Final x coordinate of the (touch) input
        "iy": None,    # Final y coordinate of the (touch) input
    }

    _UMP_supported_hit_types = [
        'pageview', 'event', 'd_proximity','d_checkin', 'd_interaction'
    ]

    def __init__(self, tracking_id, client_uuid=None, api_wrapper=None,
                 config_file_path=None, config_file_filename=None):
        """
        Constructor for creating a new Pheme Library object.

        :param tracking_id: Unique tracking ID assigned by the Pheme backend.
        :param client_uuid: Unique client identifier of the reporting device.
        :param api_wrapper: Pass in a different API handler for sending HTML
                            requests.
        :param config_file_path: Path to the configuration file consisting of
                                 generated client UUID to be reused on the next
                                 object initialisation.
        :param config_file_filename: Filename of the configuration file.
        """

        # Rename config file and/or change path if required.
        # THESE LINES HAVE TO COME FIRST IN THIS METHOD! Otherwise methods that
        # are called within the instructor won't be able to access the config.
        if config_file_filename:
            self.config_filename = config_file_filename
        else:
            self.config_filename = CONFIG_FILENAME_DEFAULT
        if config_file_path:
            self.config_filename = os.path.join(
                config_file_path, config_file_filename
            )

        # Setup the API wrapper
        api_server_config = self.get_api_server()
        api_options = {}

        if api_server_config:
            api_options = {
                "HOST": api_server_config['host'],
                "PATH": api_server_config['path'],
                "METHOD": "POST",
                "PORT": 80
            }

        if api_wrapper:
            self.api_wrapper = api_wrapper
        else:
            self.api_wrapper = APIWrapper(options=api_options)

        # Set up general parameters.
        self._UMP_general['tid'] = tracking_id
        self._UMP_general['cid'] = client_uuid or self.get_client_uuid()

    def _get_hit_type_array(self, hit_type):
        if not hit_type in self._UMP_supported_hit_types:
            raise IAexceptions.NotSupportedHitType
        return {"t": hit_type}

    def _merge_dicts(self, *args):
        merged_dict = {}
        for a in args:
            if not isinstance(a, dict):
                raise IAexceptions.VarMustBeDict
            merged_dict = dict(list(merged_dict.items()) + list(a.items()))
        return merged_dict

    def _generate_uuid(self):
        # Maybe link that somehow to the app store?
        return uuid.uuid4()

    def _save_config(self, section, option, value):
        cfg = configparser.ConfigParser()
        cfg[section] = {option: value}
        with open(self.config_filename, 'w') as configfile:
            cfg.write(configfile)

    def _generate_data_dict(self, hit_type, hit_dict):
        """
        Merge all relevant dictionaries, i.e. system info and general, to the
        specific dictionary provided by the hit type.
        """
        return_dict = self._merge_dicts(
            self._UMP_general, self._UMP_system_info, hit_type, hit_dict
        )
        return return_dict

    def set_client_uuid(self, client_uuid):
        self._UMP_general['cid'] = client_uuid

    def get_client_uuid(self):
        # Read out UUID from config or create new random UUID.
        cfg = configparser.ConfigParser()
        cfg.read(self.config_filename)
        if cfg.has_option(CONFIG_SECTION_DEFAULT, "uuid"):
            return cfg.get(CONFIG_SECTION_DEFAULT, 'uuid')
        if cfg.has_option(CONFIG_SECTION_FALLBACK, 'uuid'):
            return cfg.get(CONFIG_SECTION_FALLBACK, 'uuid')
        uuid = self._generate_uuid()
        self._save_config(CONFIG_SECTION_DEFAULT, 'uuid', uuid)
        return uuid

    def get_api_server(self):
        api_server = {
            'host': self._get_api_host(),
            'path': self._get_api_path()
        }
        if api_server['host'] and api_server['path']:
            return api_server
        return None

    def _get_api_host(self):
        # Read out the API URL from config or use default if non is specified
        cfg = configparser.ConfigParser()
        cfg.read(self.config_filename)
        if cfg.has_option(API_SERVER_CONFIG_SECTION, "api_host"):
            return cfg.get(API_SERVER_CONFIG_SECTION, "api_host")
        return None

    def _get_api_path(self):
        # Read out the API Path from config or use default if non is specified
        cfg = configparser.ConfigParser()
        cfg.read(self.config_filename)
        if cfg.has_option(API_SERVER_CONFIG_SECTION, "api_path"):
            return cfg.get(API_SERVER_CONFIG_SECTION, "api_path")
        return None

    @staticmethod
    def _start_background_thread(target, args, kwargs):
        reporting_thread = threading.Thread(
            target=target, args=args, kwargs=kwargs
        )
        reporting_thread.start()
        return reporting_thread

    def flush_client_uuid(self):
        # Delete old UUID and generate a new random UUID for this device.
        uuid = self._generate_uuid()
        self._save_config(CONFIG_SECTION_DEFAULT, 'uuid', uuid)
        return uuid

    def set_system_info(self, screen_resolution, viewable_area, screen_colours,
                        user_language, encoding='utf-8'):
        self._UMP_system_info['sr'] = screen_resolution
        self._UMP_system_info['vp'] = viewable_area
        self._UMP_system_info['de'] = encoding
        self._UMP_system_info['sd'] = screen_colours
        self._UMP_system_info['ul'] = user_language

    def track_event(self, category, action, value, label=None, time_delta=None):
        """
        Track an event of category, action, label and value.
        Category: must be string.
        Action: must be string.
        Value: string or dictionary.
        Label: must be string.
        time_delta: integer value (queue time delta in milliseconds)
        """
        event_dict = copy.deepcopy(self._UMP_event_tracking)
        event_dict['ec'] = category
        event_dict['ea'] = action
        event_dict['ev'] = value
        event_dict['el'] = label
        hit_type = self._get_hit_type_array("event")
        data = self._generate_data_dict(hit_type, event_dict)
        data['qt'] = time_delta
        self.api_wrapper.send_data(data)

    def track_event_async(self, *args, **kwargs):
        """ Tracking an event asynchronously.

        PLEASE NOTE: this is just a wrapper around `track_event`. Please
        have a look at the original method for args and kwargs.
        """
        return self._start_background_thread(
            target=self.track_event, args=args, kwargs=kwargs
        )

    def track_pageview(self, document_location, host=None, path=None,
                       title=None, descrption=None, linkid=None,
                       document_hash_md5=None, document_hash_sha1=None,
                       time_delta=None):
        """
        Track pageview. Must provide document_location, lost, path, title of
        requested page or content item.
        Description, linkid and timestamp are optional.

        :param document_location:
        :param host:
        :param path:
        :param title:
        :param descrption:
        :param linkid:
        :param document_hash_md5:
        :param document_hash_sha1:
        :param timestamp:
        :param time_delta: queue time delta in milliseconds (integer value)
        """
        content_dict = copy.deepcopy(self._UMP_content_information)
        content_dict['dl'] = document_location
        content_dict['dh'] = host
        content_dict['dp'] = path
        content_dict['dt'] = title
        content_dict['cd'] = descrption

        # Extract host and path from document_location
        if not host or not path:
            parsed_url = urlparse(content_dict['dl'])
            content_dict['dh'] = parsed_url.netloc
            content_dict['dp'] = parsed_url.path

        content_dict['md5'] = document_hash_md5
        content_dict['sha1'] = document_hash_sha1
        content_dict['linkid'] = linkid
        hit_type = self._get_hit_type_array("pageview")

        data = self._generate_data_dict(hit_type, content_dict)

        # data['qt'] = time_delta   # FIXME

        self.api_wrapper.send_data(data)

    def track_pageview_async(self, *args, **kwargs):
        """ Tracking a pageview asynchronously.

        PLEASE NOTE: this is just a wrapper around `track_pageview`. Please
        have a look at the original method for args and kwargs.
        """
        return self._start_background_thread(
            target=self.track_pageview, args=args, kwargs=kwargs
        )

    def track_d_checkin(self, person_uuid=None, gender=None, age=None,
                        mood=None):
        """
        Track a person 'checking in' at a display, i.e. appearing at a display.
        This may trigger a pageview of the displayed content.

        :param person_uuid: Person's unique ID.
        :param gender: Person's gender.
        :param age: Person's age.
        :param mood: Person's mood.
        :return:
        """
        content_dict = copy.deepcopy(self._UMP_passersby_tracking)
        content_dict['v_uuid'] = person_uuid
        content_dict['ug'] = gender
        content_dict['ua'] = age
        content_dict['um'] = mood

        hit_type = self._get_hit_type_array("d_checkin")

        data = self._generate_data_dict(hit_type, content_dict)
        self.api_wrapper.send_data(data)

    def track_d_proximity(self, distance=None, metric=None,
                          interaction_type=None, direction_view=None,
                          passersby_x=None, passersby_y=None, time_spent=None,
                          person_uuid=None, gender=None, age=None, mood=None):
        """
        Track signage proximity type.

        :param distance: Distance of user to the display.
        :param metric: Metric that was used for specifying the distance.
        :param interaction_type: Type of interaction or proximity area.
        :param direction_view: Direction of view of the user compared to display
        :param passersby_x: x coordinate of passers-by
        :param passersby_y: y coordinate of passers-by
        :param time_spent: Time of a user spent at a display (or area).
        :param person_uuid: Person's unique ID.
        :param gender: Person's gender.
        :param age: Person's age.
        :param mood: Person's mood.
        :return:
        """
        content_dict = copy.deepcopy(self._UMP_d_proximity_tracking)
        content_dict["pd"] = distance
        content_dict["pm"] = metric
        content_dict["pi"] = interaction_type
        content_dict["dv"] = direction_view
        content_dict["px"] = passersby_x
        content_dict["py"] = passersby_y
        content_dict["pt"] = time_spent

        person_dict = copy.deepcopy(self._UMP_passersby_tracking)
        person_dict["v_uuid"] = person_uuid
        person_dict["ug"] = gender
        person_dict["ua"] = age
        person_dict["um"] = mood

        merged_content = self._merge_dicts(content_dict, person_dict)

        hit_type = self._get_hit_type_array("d_proximity")

        data = self._generate_data_dict(hit_type, merged_content)
        self.api_wrapper.send_data(data)

    def track_interaction(self, interaction_type, x_coordinate, y_coordinate):
        """
        Track an interaction type with the screen such as direct input.
        Please set the type to, for example, "touch" and pass through the
        corresponding coordinates.
        :param type: touch, move, ...
        :param x_coordinate: touch input coordinate
        :param y_coordinate: touch input coordinate
        :return:
        """
        event_dict = copy.deepcopy(self._UMP_d_interaction)
        event_dict['it'] = interaction_type
        event_dict['ix'] = x_coordinate
        event_dict['iy'] = y_coordinate
        hit_type = self._get_hit_type_array("d_interaction")
        data = self._generate_data_dict(hit_type, event_dict)
        self.api_wrapper.send_data(data)
