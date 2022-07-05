import sys
import logging
from conf import Conf

import common
from iotics.api.common_pb2 import Scope
from iotics.api.search_pb2 import ResponseType
from model.common import ON_EL, ON_RDF
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from samples.identity_helper import IdHelper

logger = logging.getLogger("evdemo")

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
    types = [
        f"{ON_EL}#ChargingStation",
        f"{ON_EL}#Connector",
        "http://www.productontology.org/doc/Algorithm",
        "https://data.iotics.com/app#Model",
        "http://www.productontology.org/doc/Application"
    ]
    for typ in types:
        payload = SearchPayloadBuilder()
        properties_filter = []  # exact match
        properties_filter.append(my_api.make_property_uri(f'{ON_RDF}#type', typ))
        payload.properties = properties_filter
        payload.response_type = ResponseType.FULL

        logger.debug(payload.properties)

        result_stream = my_api.search_api.dispatch_search_request(payload.build(),
                                                                  client_ref=ApiHelper.randClientRef(),
                                                                  scope=Scope.LOCAL,
                                                                  timeout=3)

        for result in my_api.search_api.process_results_stream(result_stream):
            host_id = None if result.payload.remoteHostId.value == '' else result.payload.remoteHostId.value
            # logger.debug(f"result from host: {id}")
            twins = result.payload.twins
            logger.info(f'found {len(result.payload.twins)} twins')
            for twin in twins:
                try:
                    logger.info(f'about to delete {twin.id.value}')
                    my_api.twin_api.delete_twin(twin.id.value)
                    logger.info(f'deleted {twin.id.value}')
                except Exception as ex:  # pylint: disable=broad-except
                    logger.info(f'cannot delete {twin.id.value}: {ex}')
