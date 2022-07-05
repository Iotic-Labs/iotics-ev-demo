
from distutils.debug import DEBUG
import sys
import logging
import time
import os
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from timeloop import Timeloop
import common

from conf import Conf
from iotics.api.common_pb2 import Scope
from iotics.api.search_pb2 import ResponseType
from model.charging_station_twin import ChargingStationTwin
from model.common import ON_EL, ON_RDF
from model.forecast_twin import OccupancyForecastTwin

from openchargemap.api import Api

from samples.api_helper import ApiHelper, SearchPayloadBuilder
from samples.identity_helper import IdHelper

logger = logging.getLogger("evdemo")


class AIAlgo:
    def __init__(self, conf: Conf, api: ApiHelper, ev_api: Api, executor: ThreadPoolExecutor):
        self.api = api
        self.ev_api = ev_api
        self.conf = conf
        self.known_twins = {}
        self.executor = executor
        self.model_twin_did = None

    def make_if_not_known(self, twin):
        def task():
            try:
                known = self.known_twins.get(twin.twin_did)
                if not known:
                    logger.info(f"making: {twin.twin_did}")
                    twin.make()
                    self.known_twins[twin.twin_did] = twin
                else:
                    logger.debug(f"already registered {twin.twin_did}")
            except Exception as ex:  # pylint: disable=broad-except
                logger.error(f"err when making {twin.twin_did}: {ex}")

        self.executor.submit(task)

    def twin_manager(self):
        logger.info("managing thread started")
        tl = Timeloop()
        searchClientRef = ApiHelper.randClientRef()

        def process_searches(result):
            twins = result.payload.twins
            if len(twins) > 0:
                logger.info(f'processing {len(twins)} twins')
                for t in twins:
                    logger.info(f'processing {t.id.value}')
                    try:
                        ev_charger_twin = ChargingStationTwin(
                            my_api,
                            model_twin_did=None, charger_model_twin_did=None,
                            charger_station_twin=t, host_id=result.payload.remoteHostId.value)
                        occupancy = OccupancyForecastTwin(my_api,
                                                          model_twin_did=self.model_twin_did,
                                                          charging_station_twin=ev_charger_twin)

                        self.make_if_not_known(occupancy)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error(f'unable to register algo twin for {ev_charger_twin}: {exc}')

        my_api.search_api.register_callback(searchClientRef, process_searches)
        self.executor.submit(my_api.search_api.receive_search_responses)

        @tl.job(interval=timedelta(seconds=my_conf.ev_api_poll_interval))
        def check_charger_twins_periodically():
            logger.info("searching...")
            payload = SearchPayloadBuilder()
            properties_filter = []  # exact match
            properties_filter.append(my_api.make_property_uri(
                f'{ON_RDF}#type',
                f'{ON_EL}#ChargingStation')
            )
            payload.properties = properties_filter
            payload.response_type = ResponseType.FULL

            my_api.search_api.dispatch_search_request_async(payload.build(),
                                                            client_ref=searchClientRef,
                                                            scope=Scope.GLOBAL,
                                                            timeout=5)

        # kick off the first fetch
        check_charger_twins_periodically()

        tl.start()

    def twin_share(self):
        logger.info("sharing thread started")
        tl = Timeloop()

        @tl.job(interval=timedelta(seconds=my_conf.algo_updates_publish_interval))
        def share_periodically():
            copy = self.known_twins.copy()
            for item in copy.items():
                twin_did = item[0]
                twin = item[1]
                logger.info(f"sharing for twin {twin_did}")
                twin.publish()

        tl.start()

    def make_models(self):
        try:
            self.model_twin_did = OccupancyForecastTwin.make_model(my_api)
            logger.info(f"Made model for OccupancyForecastTwin: {self.model_twin_did}")
        except Exception as ex:  # pylint: disable=broad-except
            logger.error(f'unable to make model: {ex}')

    def start(self):
        self.make_models()
        self.executor.submit(self.twin_manager)
        self.executor.submit(self.twin_share)


if __name__ == '__main__':
    # read config
    my_conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not my_conf.init_and_validate() else print("config valid")  # pylint: disable=expression-not-assigned
    # init logger
    common.init_logger()

    # make Identity helper
    id_helper = IdHelper(my_conf.api_endpoint,
                         user_seed=my_conf.user_seed(),
                         user_key_name=my_conf.user_key_name,
                         user_name=my_conf.user_name,
                         agent_seed=my_conf.agent_seed(),
                         agent_key_name=my_conf.agent_key_name,
                         agent_name=my_conf.agent_name,
                         jwt_duration=my_conf.jwt_token_expiry)

    my_api = ApiHelper(id_helper)

    publisher = AIAlgo(conf=my_conf,
                       api=my_api,
                       ev_api=Api(),
                       executor=ThreadPoolExecutor(100))

    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
