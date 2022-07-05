
import sys
import logging
import time
import os
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from timeloop import Timeloop

from conf import Conf
from openchargemap.api import Api, EvCharger
from model.charging_station_twin import ChargingStationTwin
from model.connection_twin import ConnectionTwin

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper

import common

logger = logging.getLogger("evdemo")


class Publisher:
    def __init__(self, conf: Conf, api: ApiHelper, ev_api: Api, executor: ThreadPoolExecutor):
        self.api = api
        self.ev_api = ev_api
        self.conf = conf
        self.known_twins = {}
        self.executor = executor
        self.model_twin_did = None
        self.charger_model_twin_did = None

    def make_if_not_known(self, twin: ChargingStationTwin):
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
        # task()

    def process_fetched_ev_charging_station(self, evCharger: EvCharger):
        try:
            logger.info(f"received: {evCharger.name}")
            twin = ChargingStationTwin(self.api,
                                       model_twin_did=self.model_twin_did,
                                       charger_model_twin_did=self.charger_model_twin_did,
                                       ev=evCharger,
                                       force_create=self.conf.force_create_twins)
            self.make_if_not_known(twin)
            for twin in twin.connectionTwins:
                self.make_if_not_known(twin)
        except Exception as ex:  # pylint: disable=broad-except
            logger.error(f"err when processing fetched charger {evCharger.name}: {ex}")

    def twin_manager(self):
        logger.info("managing thread started")
        tLoop = Timeloop()

        @tLoop.job(interval=timedelta(seconds=my_conf.ev_api_poll_interval))
        def check_downstream_api_periodically():
            logger.debug("fetching ev charger data from remote")
            self.executor.submit(self.ev_api.fetch(callback=self.process_fetched_ev_charging_station))
        # kick off the first fetch
        check_downstream_api_periodically()

        tLoop.start()

    def twin_share(self):
        logger.info("sharing thread started")
        tLoop = Timeloop()

        @tLoop.job(interval=timedelta(seconds=my_conf.ev_updates_publish_interval))
        def share_periodically():
            copy = self.known_twins.copy()
            for item in copy.items():
                twin_did = item[0]
                twin = item[1]
                logger.info(f"sharing for twin {twin_did}")
                twin.publish()

        tLoop.start()

    def make_models(self):
        # try:
        self.model_twin_did = ChargingStationTwin.makeModel(self.api)
        logger.info(f"Made model for ChargingStationTwin: {self.model_twin_did}")
        self.charger_model_twin_did = ConnectionTwin.makeModel(self.api)
        logger.info(f"Made model for ConnectionTwin: {self.charger_model_twin_did}")
        # except Exception as ex:
        #    logger.error(f'unable to make model: {ex}')

    def start(self):
        self.make_models()
        self.executor.submit(self.twin_manager)
        self.executor.submit(self.twin_share)


if __name__ == '__main__':
    # read config
    my_conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not my_conf.init_and_validate() else print("config valid")  # pylint: disable=expression-not-assigned
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

    publisher = Publisher(conf=my_conf,
                          api=my_api,
                          ev_api=Api(),
                          executor=ThreadPoolExecutor(os.cpu_count() * 4))

    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
