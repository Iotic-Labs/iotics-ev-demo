import json
import logging
from iotics.api.common_pb2 import Visibility

from openchargemap.api import EvConnection

from datetime import datetime, timezone

from model.common import ON_RDFS, ON_RDF, ON_SCH, ON_EL, TAG, common_properties, make_model_generic
from samples.api_helper import ApiHelper

logger = logging.getLogger("evdemo")


class ConnectionTwin:
    FEEDNAME = "is_operational"

    def __init__(self, api: ApiHelper, parent_twin_did: str, model_twin_did: str, ev: EvConnection, force_create: bool = False):
        self.api = api
        self.parent_twin_did = parent_twin_did
        self.ev = ev
        self.twin_did = None
        self.model_twin_did = model_twin_did
        self.force_create = force_create
        if not self.ev.ID:
            Exception(f'unable to create ev charger {ev.name}')
        self.twin_did = self.api.id_helper.create_twin_did_and_register(ev.name)
        if not self.twin_did:
            Exception(f'unable to create identity for ev charger {ev.name}')

    @staticmethod
    def makeModel(api: ApiHelper):
        twin_did = api.id_helper.create_twin_did_and_register("UrbanIOTConnectorTwinModel")
        make_model_generic(api, twin_did=twin_did, defined_rdf_types=[f'{ON_EL}#Connector'], colour="#374638",
                           label="Urban IOT Electric Connector Model", comment=f'the model of a {TAG} Connector', extraProps=[])
        return twin_did

    def publish(self):
        operation_json = json.dumps({"operational": self.ev.is_operational})
        logger.debug(f"sharing for {self.ev.name}: {operation_json}")
        self.api.feed_api.share_feed_data(self.twin_did, self.FEEDNAME, operation_json)

    @property
    def label(self):
        l = "EV Connection"
        if self.ev.evCharger.operator:
            l = f"{l} - {self.ev.evCharger.operator}"
        l = f"{l} @ {self.ev.evCharger.place}"
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
        self.api.twin_api.update_twin_visibility(self.twin_did, Visibility.PUBLIC)
        self.api.twin_api.update_twin_location(self.twin_did, tuple(self.ev.evCharger.lat_lon))

        properties = self.props
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', self.label))
        properties.append(self.api.make_property_string(f'{ON_RDFS}#comment', f'{self.ev.evCharger.comments} {TAG}'))
        properties.append(self.api.make_property_string('http://schema.org/name', self.api.id_helper.agent_name))
        properties.append(self.api.make_property_uri(
            'http://data.iotics.com/public#hostAllowList', 'http://data.iotics.com/public#allHosts'))

        self.api.twin_api.replace_twin_properties(self.twin_did, properties)
        # update_twin_response = self.api.twin_api.replace_twin_properties(self.twin_did, properties)
        # logger.debug(update_twin_response)

        self.api.feed_api.create_feed(self.twin_did, self.FEEDNAME)

        values = []
        values.append(self.api.feed_api.make_value(
            "operational", "value set to 'true' if the connection is operational", None, "boolean"))

        properties = []
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', f"is_operational"))
        properties.append(self.api.make_property_string(
            f'{ON_RDFS}#comment', f'whether the connection is operational or not {TAG}'))
        self.api.feed_api.update_feed(self.twin_did, self.FEEDNAME, values, properties, store_last=True)

    @property
    def props(self):
        d = datetime.now(tz=timezone.utc).isoformat()
        return [
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       f'{ON_EL}#Connector'),
            self.api.make_property_literal(f'{ON_EL}#maxAmperageInA',
                                           str(self.ev.amps),
                                           "decimal"),
            self.api.make_property_literal(f'{ON_EL}#maxPowerInKW',
                                           str(self.ev.power_kw),
                                           "decimal"),
            self.api.make_property_literal(f'{ON_EL}#maxVoltageInV',
                                           str(self.ev.voltage),
                                           "decimal"),
            self.api.make_property_string(f'{ON_EL}#hasPowerSupply',
                                          self.ev.current_type),
            self.api.make_property_bool(f'{ON_EL}#isFastCharger',
                                        bool(self.ev.is_fast_charge_capable)),
            self.api.make_property_bool(f'{ON_EL}#isOperational',
                                        bool(self.ev.is_operational)),
            self.api.make_property_string(f'{ON_SCH}/name',
                                          self.ev.formal_name),
            self.api.make_property_uri(f'{ON_EL}#usesChargingStation', self.parent_twin_did),
        ] + common_properties(self.api, model_twin_did=self.model_twin_did, author=f'Agent:{self.api.id_helper.agent_name}')
