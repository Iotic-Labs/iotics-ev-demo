import logging
import sys
from xmlrpc.client import Boolean

from conf import Conf
import common
from model.common import ON_EL, ON_RDF
import os
import time

from pprint import pprint as pp

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from concurrent.futures import ThreadPoolExecutor

from iotics.api.common_pb2 import Scope
from iotics.api.search_pb2 import ResponseType

logger = logging.getLogger("evdemo")


if __name__ == '__main__':
    # read config
    my_conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not my_conf.init_and_validate() else print("")
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

    payload = SearchPayloadBuilder()
    properties_filter = []  # exact match
    properties_filter.append(my_api.make_property_uri(
        f'{ON_RDF}#type',
        f'{ON_EL}#ChargingStation')
    )
    payload.properties = properties_filter
    payload.response_type = ResponseType.FULL
    executor = ThreadPoolExecutor(os.cpu_count() * 4)

    def search_response_callback(search_result) -> Boolean:
        host = "localhost"
        if(len(search_result.payload.remoteHostId.value) > 0):
            host = search_result.payload.remoteHostId.value
        twins = search_result.payload.twins
        if len(twins) > 0:
            logger.info(f'found to {len(twins)} twins in {host}')
            for t in twins:
                logger.info(f'{t.id.value}')
        else:
            logger.info(f'no twins found in {host}')

    # make a clientRef to link request and response
    clientRef = ApiHelper.randClientRef()
    # responses with this clientRef will be dispatched to the callback
    my_api.search_api.register_callback(clientRef, search_response_callback)

    future = executor.submit(my_api.search_api.receive_search_responses, 3)

    # a search with clientRef - one can make different searches with different
    #  clientRef to dispatch to separate callbacks
    my_api.search_api.dispatch_search_request_async(payload.build(),
                                                    client_ref=clientRef,
                                                    scope=Scope.GLOBAL,
                                                    timeout=3)

    # wait for the receive_search_response to terminate
    logger.info("result of future: " + future.result())
    my_api.grpc_channel.close()
    executor.shutdown()
