import logging
import sys
from model.common import ON_EL, ON_RDF

from samples.identity_helper import IdHelper
from iotics.api.common_pb2 import Scope
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from iotics.api.search_pb2 import ResponseType

from conf import Conf
import common

logger = logging.getLogger("evdemo")

if __name__ == '__main__':
    # read config
    conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not conf.init_and_validate() else print("")   # pylint: disable=expression-not-assigned
    # init logger
    common.init_logger()

    # make auth facade
    id_helper = IdHelper(conf.api_endpoint,
                         user_seed=conf.user_seed(),
                         user_key_name=conf.user_key_name,
                         user_name=conf.user_name,
                         agent_seed=conf.agent_seed(),
                         agent_key_name=conf.agent_key_name,
                         agent_name=conf.agent_name,
                         jwt_duration=20)

    api = ApiHelper(id_helper)

    # we make a follower - the follower is the twin that represents this agent in Iotics for the
    # purpose fo proxying follow requests.
    follower_app_did = common.make_or_get_follower(api)

    # check our follower twin looks like we'd hope
    common.log_description(api.twin_api.describe_twin(follower_app_did))

    logger.info('')
    logger.info("=====================================")
    logger.info('')
    logger.info("Searching for Operational Connectors...")

    payload = SearchPayloadBuilder()

    properties_filter = []  # exact match
    properties_filter.append(api.make_property_bool(f'{ON_EL}#isOperational', True))
    properties_filter.append(api.make_property_uri(f'{ON_RDF}#type', f'{ON_EL}#Connector'))
    payload.properties = properties_filter
    payload.response_type = ResponseType.FULL

    result_stream = api.search_api.dispatch_search_request(payload.build(),
                                                           client_ref=ApiHelper.randClientRef(),
                                                           scope=Scope.GLOBAL,
                                                           timeout=3)

    listReplies = []
    for result in api.search_api.process_results_stream(result_stream):
        # logger.debug(result)
        listReplies.append(result)
        logger.debug(len(result.payload.twins))
        logger.debug(80 * "*")

    logger.info("Got results, calculating total power in kW...")

    # we flatten the listReplies to get the list of twins that we can then further process
    twins = common.flatten(map(lambda result: result.payload.twins, listReplies))
    all_props = common.flatten(map(lambda x: x.properties, twins))
    power_props = filter(lambda x: x.key == f"{ON_EL}#maxPowerInKW", all_props)
    power_vals = map(float, filter(lambda x: x, map(lambda p: common.as_value(p), power_props))
                     )  # pylint: disable=unnecessary-lambda
    tot = sum(power_vals)
    logger.info('')
    logger.info(f'consumed a total of {tot} kW')

    # search by location
    # future = messaging.sync_search(
    #     location=[52.1913, 0.1519],
    #     radius_km=0.1,
    # )

    logger.info('')
    logger.info("=====================================")
    logger.info('')
    logger.info("Searching for all connectors and chargers in the ev demo...")

    properties_filter = []  # exact match
    # properties_filter.append(api.make_property_bool('http://demo.iotics.com/ont/demo/isDemoTwin', True))   # should be this
    properties_filter.append(api.make_property_string(
        'http://demo.iotics.com/ont/demo/isDemoTwin', "true"))  # this should work
    payload.properties = properties_filter
    payload.response_type = ResponseType.FULL

    result_stream = api.search_api.dispatch_search_request(payload.build(),
                                                           client_ref=ApiHelper.randClientRef(),
                                                           timeout=3)

    listReplies = []
    for result in api.search_api.process_results_stream(result_stream):
        # logger.debug(result)
        listReplies.append(result)
        logger.debug(len(result.payload.twins))
        logger.debug(80 * "*")

    counts = {}
    for r in listReplies:
        for e in r.payload.twins:
            # logger.info(f"found {e.id.value}: {e.label}")
            for p in e.properties:
                if p.key == f'{ON_RDF}#type':
                    c = counts.get(common.as_value(p), 0) + 1
                    counts[common.as_value(p)] = c

    logger.info("")
    logger.info('Found: ')
    for key, value in counts.items():
        logger.info(f'> {key}, {value}')
    logger.info("")
    logger.info("=====================================")

    logger.info("")
    logger.info("Describe the first twin we got back")

    if len(counts) > 0:
        # find a charger
        twins = common.flatten(map(lambda result: result.payload.twins, listReplies))
        first_twin_did = twins[0].id.value
        # print out its description
        common.log_description(api.twin_api.describe_twin(first_twin_did))
