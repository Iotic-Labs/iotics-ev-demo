import json
import logging
from iotics.api.common_pb2 import Visibility

from model.connection_twin import ConnectionTwin
from openchargemap.api import EvCharger

from datetime import datetime, timezone

from model.common import ON_RDF, ON_RDFS, ON_SCH, ON_EL, TAG, common_properties, make_model_generic
from samples.api_helper import ApiHelper

logger = logging.getLogger("evdemo")


class ChargingStationTwin:
    def __init__(self,
                 api: ApiHelper,
                 model_twin_did: str,
                 charger_model_twin_did: str,
                 ev: EvCharger = None,
                 host_id: str = None,
                 charger_station_twin=None,
                 force_create: bool = False):
        self.api = api
        self.host_id = host_id
        self.evCharger = ev
        self.twin_did = None
        self.model_twin_did = model_twin_did
        self.charger_model_twin_did = charger_model_twin_did
        self.force_create = force_create

        try:
            if self.evCharger is not None:
                # making it as the request comes from the publisher
                if not self.evCharger.ID:
                    Exception(f'unable to create EV Charging Station {self.evCharger.name}')
                self.twin_did = self.api.id_helper.create_twin_did_and_register(self.evCharger.name)
                if not self.twin_did:
                    Exception(f'unable to create identity for EV Charging Station {self.evCharger.name}')
            else:
                # loading it as the request comes from the algo
                self.twin_did = charger_station_twin.id.value
                ID = ""
                for p in charger_station_twin.properties:
                    if p.key == "http://schema.org/identifier":
                        ID = p.stringLiteralValue.value
                self.evCharger = EvCharger({
                    "ID": ID
                })
        except Exception as ex:
            logging.error(f'problems making a charging station twin {ex}')

    @staticmethod
    def makeModel(api: ApiHelper):
        twin_did = api.id_helper.create_twin_did_and_register("UrbanIOTChargingStationTwinModel")
        make_model_generic(api, twin_did=twin_did, defined_rdf_types=[
            f'{ON_SCH}/Place',
            f'{ON_SCH}/Service',
            f'{ON_EL}#ChargingStation'],
            colour="#234532",
            label="Urban IOT Electric Charging Station Model",
            comment=f'the model of a {TAG} ChargingStation',
            extraProps=[])
        return twin_did

    @property
    def connectionTwins(self):
        twins = []
        for c in self.evCharger.connections:
            twins.append(ConnectionTwin(self.api,
                                        parent_twin_did=self.twin_did,
                                        model_twin_did=self.charger_model_twin_did,
                                        ev=c, force_create=self.force_create))
        return twins

    def publish(self):
        avail = json.dumps({"v": self.evCharger.is_live})
        self.api.feed_api.share_feed_data(self.twin_did, "availability", avail)

        operational = json.dumps({"v": self.evCharger.is_operational})
        self.api.feed_api.share_feed_data(self.twin_did, "operationality", operational)

        logger.debug(f"shared for {self.evCharger.name}: {avail} and {operational}")

    @property
    def label(self):
        l = "EV Station"
        if self.evCharger.operator:
            l = f"{l} - {self.evCharger.operator}"
        l = f"{l} @ {self.evCharger.place}"
        return l

    # def exists(self, twin_id):
    #     try:
    #         self.qapi.describe_twin(twin_id=twin_id)
    #         return True
    #     except:
    #         return False

    def make(self):
        # if not self.force_create and self.exists(twin_id=self.twin_did):
        #     return

        self.api.twin_api.create_twin(self.twin_did)

        logger.info(f"CHARGER {self.twin_did}")

        self.api.twin_api.update_twin_visibility(self.twin_did, Visibility.PUBLIC)
        self.api.twin_api.update_twin_location(self.twin_did, tuple(self.evCharger.lat_lon))

        properties = self.props
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', self.label))
        properties.append(self.api.make_property_string(f'{ON_RDFS}#comment', f'{self.evCharger.comments} {TAG}'))
        properties.append(self.api.make_property_string('http://schema.org/name', self.api.id_helper.agent_name))
        properties.append(self.api.make_property_uri(
            'http://data.iotics.com/public#hostAllowList', 'http://data.iotics.com/public#allHosts'))

        update_twin_response = self.api.twin_api.replace_twin_properties(self.twin_did, properties)
        # logger.debug(update_twin_response)

        feed_name = "availability"
        self.api.feed_api.create_feed(self.twin_did, feed_name)

        values = []
        values.append(self.api.feed_api.make_value(
            "v", "value set to 'true' if the charger is available", None, "boolean"))

        properties = []
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', f"availability of this charging station"))
        properties.append(self.api.make_property_string(
            f'{ON_RDFS}#comment', f'whether the station is available or not {TAG}'))
        self.api.feed_api.update_feed(self.twin_did, feed_name, values, properties, store_last=True)

        feed_name = "operationality"
        self.api.feed_api.create_feed(self.twin_did, feed_name)

        values = []
        values.append(self.api.feed_api.make_value(
            "v", "value set to 'true' if the charger is operational", None, "boolean"))

        properties = []
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', f"operationality of this charging station"))
        properties.append(self.api.make_property_string(
            f'{ON_RDFS}#comment', f'whether the station is operational or not {TAG}'))
        self.api.feed_api.update_feed(self.twin_did, feed_name, values, properties, store_last=True)

    @property
    def props(self):
        return [
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       f'{ON_EL}#ChargingStation'),
            self.api.make_property_string(f'{ON_SCH}/identifier',
                                          f'{self.evCharger.ID}'),
            self.api.make_property_string('http://www.productontology.org/doc/UUID',
                                          self.evCharger.uuid),
            self.api.make_property_string(f'{ON_EL}#operatedBy',
                                          self.evCharger.operator),
            self.api.make_property_string(f'{ON_SCH}/description',
                                          self.evCharger.place),
            self.api.make_property_string(f'{ON_SCH}/price',
                                          self.evCharger.usage_cost),
            self.api.make_property_bool(f'{ON_EL}#isPrivate',
                                        str(self.evCharger.has_free_access)),
            self.api.make_property_string(f'{ON_SCH}/address',
                                          self.evCharger.address),
            self.api.make_property_string('http://demo.iotics.com/ont/ev/date_last_status_update',
                                          self.evCharger.date_last_status_update),
            self.api.make_property_string('http://demo.iotics.com/ont/ev/date_last_verified',
                                          self.evCharger.date_last_verified),
            self.api.make_property_literal(f'{ON_EL}#numberOfConnectors',
                                           str(self.evCharger.n_points),
                                           "decimal"),
        ] + common_properties(self.api, model_twin_did=self.model_twin_did, author=f'Agent:{self.api.id_helper.agent_name}')
