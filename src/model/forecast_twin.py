import json
import logging
from iotics.api.common_pb2 import Visibility
from model.charging_station_twin import ChargingStationTwin
from model.common import ON_EL, ON_RDFS, ON_RDF, TAG, common_properties, make_model_generic

from forecast_ai.algo import EvChargeOccupancyPredictor


from samples.api_helper import ApiHelper

logger = logging.getLogger("evdemo")


class OccupancyForecastTwin:
    FEED1_ID = "forecast_1h"
    FEED2_ID = "forecast_2h"

    def __init__(self, api: ApiHelper,
                 charging_station_twin: ChargingStationTwin,
                 model_twin_did: str,
                 occupancy_ai: EvChargeOccupancyPredictor = EvChargeOccupancyPredictor(),
                 force_create: bool = False):
        self.occupancy_ai = occupancy_ai
        self.api = api
        self.model_twin_did = model_twin_did
        self.charging_station_twin = charging_station_twin
        self.force_create = force_create
        self.twin_did = self.api.id_helper.create_twin_did_and_register(
            f'Forecast_algo_for_{charging_station_twin.evCharger.ID}')

    @staticmethod
    def make_model(api: ApiHelper):
        twin_did = api.id_helper.create_twin_did_and_register("AlgorithmTwinModel")
        make_model_generic(api, twin_did, defined_rdf_types=['http://www.productontology.org/doc/Algorithm',
                                                             'http://www.productontology.org/doc/Linear_regression',
                                                             'http://www.productontology.org/doc/Predictive_analytics',
                                                             'http://www.productontology.org/doc/Forecast'
                                                             ], colour="#563423",
                           label="Prediction Algo Demo Model", comment=f'the model of a {TAG} Prediction Algorithm', extraProps=[])
        return twin_did

    def publish(self):
        forecast1_json = json.dumps({"1h": self.occupancy_ai.busy_forecast_h1_prob})
        self.api.feed_api.share_feed_data(self.twin_did, self.FEED1_ID, forecast1_json)
        forecast2_json = json.dumps({"2h": self.occupancy_ai.busy_forecast_h2_prob})
        self.api.feed_api.share_feed_data(self.twin_did, self.FEED2_ID, forecast2_json)
        logger.debug(
            f"sharing for charger {self.charging_station_twin.evCharger.name}: {forecast1_json} and {forecast2_json}")

    @property
    def label(self):
        return f'Forecast for {self.charging_station_twin.evCharger.name}'

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

        logger.info(f"FORECAST_AI {self.twin_did}")

        self.api.twin_api.update_twin_visibility(self.twin_did, Visibility.PRIVATE)

        properties = self.props
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', self.label))
        properties.append(self.api.make_property_string(f'{ON_RDFS}#comment', f'{self.label} {TAG}'))
        properties.append(self.api.make_property_string('http://schema.org/name', self.api.id_helper.agent_name))
        properties.append(self.api.make_property_uri(
            'http://data.iotics.com/public#hostAllowList', 'http://data.iotics.com/public#noHosts'))

        self.api.twin_api.replace_twin_properties(self.twin_did, properties)
        # update_twin_response = self.api.twin_api.replace_twin_properties(self.twin_did, properties)
        # logger.debug(update_twin_response)

        self.api.feed_api.create_feed(self.twin_did, self.FEED1_ID)

        values = []
        values.append(self.api.feed_api.make_value(
            "1h", "number between 0 and 1, with 0 meaning certainly free in 1 hour", None, "decimal"))

        properties = []
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', "busy forecast in 1 hours"))
        properties.append(self.api.make_property_string(
            f'{ON_RDFS}#comment', f'the probability for the linked Charging Station to be busy in 1 or 2 hours {TAG}'))
        self.api.feed_api.update_feed(self.twin_did, self.FEED1_ID, values, properties, store_last=True)

        self.api.feed_api.create_feed(self.twin_did, self.FEED2_ID)

        values = []
        values.append(self.api.feed_api.make_value(
            "2h", "number between 0 and 1, with 0 meaning certainly free in 2 hours", None, "decimal"))

        properties = []
        properties.append(self.api.make_property_string(f'{ON_RDFS}#label', "busy forecast in 2 hours"))
        properties.append(self.api.make_property_string(
            f'{ON_RDFS}#comment', f'the probability for the linked Charging Station to be busy in 1 or 2 hours {TAG}'))
        self.api.feed_api.update_feed(self.twin_did, self.FEED1_ID, values, properties, store_last=True)

    @property
    def props(self):
        h = self.charging_station_twin.host_id
        if h is None:
            h = "did:iotics:none"
        return [
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       'http://www.productontology.org/doc/Algorithm'),
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       'http://www.productontology.org/doc/Linear_regression'),
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       'http://www.productontology.org/doc/Predictive_analytics'),
            self.api.make_property_uri(f'{ON_RDF}#type',
                                       'http://www.productontology.org/doc/Forecast'),
            self.api.make_property_literal('http://data.iotics.com/iotics/host_id',
                                           h,
                                           None),  # TODO not sure about this. Literal with no datatype - should be a URI?
            self.api.make_property_uri(f'{ON_EL}#uses_charging_station',
                                       self.charging_station_twin.twin_did),
        ] + common_properties(self.api, model_twin_did=self.model_twin_did, author=f'Agent:{self.api.id_helper.agent_name}')
