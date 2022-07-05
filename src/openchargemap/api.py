import ijson
import os

from collections.abc import Callable

import requests
import ijson
from urllib.parse import urljoin, urlencode

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random

# A utility class that implements null object pattern for dicts


class NoneDict(dict):
    def getOpt(self, key):
        try:
            v = dict.get(self, key)
            return v if v else {}
        except:
            return {}

    def __getitem__(self, key):
        try:
            return dict.get(self, key)
        except:
            return None

# An utility class that peeks at data into the json from the downstream API


class EvCharger:
    def __init__(self, raw: dict):
        self.raw = NoneDict(raw)

    @property
    def connections(self):
        feeds = []
        for c in self.raw.get("Connections"):
            conn = EvConnection(evCharger=self, raw=c)
            feeds.append(conn)
        return feeds

    @property
    def ID(self):
        return self.raw.get("ID")

    @property
    def name(self):
        return f"EV_ChargingStation_{self.ID}"

    @property
    def license(self):
        title = self.raw.getOpt("DataProvider").get("Title")
        license = self.raw.getOpt("DataProvider").get("License")
        if title and license:
            return f"{title}. {license}"
        if title:
            return title
        if license:
            return license
        return "unknown"

    @property
    def label(self):
        label = self.name
        if self.operator:
            label = f"EVC {self.operator}"
        if self.place:
            label += f" ({self.place})"

            label = self.name
        return label

    @property
    def comments(self):
        gc = self.raw.get("GeneralComments")
        if gc:
            return gc
        return "none available"

    @property
    def uuid(self):
        return self.raw.get("UUID").strip()

    @property
    def place(self):
        ai = self.raw.getOpt("AddressInfo")
        t = ai.get("Title")
        if t:
            return t
        return "place unknown"

    @property
    def address(self):
        ai = NoneDict(self.raw.getOpt("AddressInfo"))
        tn = ai.get("Town")
        cc = ai.get("StateOrProvince")
        c = ai.getOpt("Country").get("Title")
        res = ""
        if tn:
            res = res + tn + ","
        if cc:
            res = res + cc + ","
        if c:
            res = res + c + ","
        return res

    @property
    def operator(self):
        return self.raw.getOpt("OperatorInfo").get("Title")

    @property
    def has_free_access(self):
        v = self.raw.getOpt("UsageType").get("IsMembershipRequired") and \
            self.raw.getOpt("UsageType").get("IsAccessKeyRequired")
        return str(v).lower()

    @property
    def is_operational(self):
        return self.raw.getOpt("StatusType").get("IsOperational")

    @property
    def is_live(self):
        if random.randint(1, 10) <= 2:
            return False
        return True
        # return self.raw.getOpt("SubmissionStatus").get("IsLive")

    @property
    def usage_cost(self):
        return self.raw.get("UsageCost")

    @property
    def date_last_verified(self):
        return self.raw.get("DateLastVerified")

    @property
    def date_last_status_update(self):
        return self.raw.get("DateLastStatusUpdate")

    @property
    def n_points(self):
        return self.raw.get("NumberOfPoints")

    @property
    def lat_lon(self):
        lat = self.raw.getOpt("AddressInfo").get("Latitude")
        lon = self.raw.getOpt("AddressInfo").get("Longitude")
        if lat and lon:
            return [float(lat), float(lon)]
        return []

    @property
    def is_located(self):
        return len(self.lat_lon) == 2


class EvConnection:
    def __init__(self, evCharger: EvCharger, raw: dict):
        self.raw = NoneDict(raw)
        self.evCharger = evCharger

    @property
    def name(self):
        return f"EV_Connection_{self.evCharger.ID}_{self.ID}"

    @property
    def ID(self):
        return self.raw.get("ID")

    @property
    def formal_name(self):
        return self.raw.getOpt("ConnectionType").get("FormalName")

    @property
    def is_operational(self):
        if random.randint(1, 100) <= 25:
            return "false"
        return "true"
        # return str(self.raw.getOpt("StatusType").get("IsOperational")).lower()

    @property
    def is_fast_charge_capable(self):
        return str(self.raw.getOpt("Level").get("IsFastChargeCapable")).lower()

    @property
    def label(self):
        label = self.name
        if self.formal_name:
            label = f"EVC {self.formal_name}"
        return label

    @property
    def comments(self):
        c = self.raw.getOpt("Level").get("Comments")
        if c:
            return c
        return "none available"

    @property
    def amps(self):
        a = self.raw.get("Amps")
        if a == None:
            return 0
        return a

    @property
    def voltage(self):
        v = self.raw.get("Voltage")
        if v == None:
            return 0
        return v

    @property
    def power_kw(self):
        p = self.raw.get("PowerKW")
        if p == None:
            return 0.0
        return self.raw.get("PowerKW")

    @property
    def current_type(self):
        return self.raw.getOpt("CurrentType").get("Title").strip()


class Api:
    def __init__(self):
        pass

    # fetches data from the remote API and parses the result to the callback

    def fetch(self, callback):
        filepath = os.getenv("EV_API_FILE_PATH", "src/openchargemap/data_GB.json")
        if not filepath is None:
            return self.file_fetch(filepath=filepath, callback=callback)

        return self.remote_fetch(callback=callback)

    def file_fetch(self, filepath, callback):
        dataFile = os.path.abspath(filepath)
        with open(dataFile, 'r') as f:
            items = ijson.items(f, 'item')  # streaming parser
            for i in items:
                callback(EvCharger(i))

    def remote_fetch(self, callback):
        cli = OpenchargemapClient(
            api_key=os.getenv("OPENCHARGEMAP_APIKEY"),
            api_url=os.getenv("OPENCHARGEMAP_APIURL", "https://api.openchargemap.io/v3/poi"),
            countrycode=os.getenv("OPENCHARGEMAP_COUNTRYCODE", "GB"),
            maxresults=os.getenv("OPENCHARGEMAP_MAXRESULTS", "10"),
        )
        cli.get(callback=callback)
        pass


class MyDict:
    def __init__(self):
        self.map = {}

    def add_if(self, key, val):
        if val:
            self.map[key] = val

        return self


class OpenchargemapClient:
    def __init__(self,
                 api_key,
                 api_url,
                 countrycode="GB",
                 maxresults=10,
                 compact=True,
                 verbose=False,
                 retry_total=1000,
                 retry_backoff_factor=1):
        if not api_key:
            raise Exception("missing Openchargemap api key")

        self.api_key = api_key
        self.api_url = api_url

        self.params = MyDict()
        self.params.add_if(
            "maxresults", maxresults).add_if(
            "countrycode", countrycode).add_if(
            "compact", compact).add_if(
            "verbose", verbose).add_if(
            "key", self.api_key).add_if(
            "output", "json")
        self.retry_config = Retry(total=retry_total, backoff_factor=retry_backoff_factor)

    def get(self, callback, error_callback):
        s = requests.Session()
        s.mount('https://', HTTPAdapter(max_retries=self.retry_config))
        try:
            query = "?" + urlencode(self.params.map)
            url = urljoin(self.api_url, query)
            print(f"getting data from {url}")
            with s.get(url, stream=True) as resp:
                if resp.status_code > 399:
                    return f"unable to fetch [{resp.status_code}]: {resp.text}"
                items = ijson.items(resp.text, 'item')  # streaming parser
                for i in items:
                    callback(EvCharger(i))
        except Exception as e:
            error_callback(e)
