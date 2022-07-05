import logging
import sys
from iotics.api.common_pb2 import Scope
from iotics.api.search_pb2 import ResponseType
from model.common import ON_EL, ON_RDF

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from conf import Conf
import common


logger = logging.getLogger("evdemo")


def log_feed_callback(message):
    # logger.debug(message)
    # sys.exit()
    interest = message.payload.interest
    msg_feed = interest.followedFeed.feed
    feed_str = f"{msg_feed.twinId.value}/{msg_feed.id.value}"
    # data = base64.b64decode(message.payload.feedData.data).decode("utf-8")
    logger.info(f"{feed_str}: {message.payload.feedData.data}")


if __name__ == '__main__':
    # read config
    conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not conf.init_and_validate() else print("")  # pylint: disable=expression-not-assigned
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
                         jwt_duration=conf.jwt_token_expiry)

    api = ApiHelper(id_helper)

    # we make a follower - the follower is the twin that represents this agent in Iotics for the
    # purpose fo proxying follow requests.
    follower_twin_id = common.make_or_get_follower(api)

    # check our follower twin looks like we'd hope
    common.log_description(api.twin_api.describe_twin(follower_twin_id))

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

    try:
        stops = []
        for result in api.search_api.process_results_stream(result_stream):
            host_id = None if result.payload.remoteHostId.value == '' else result.payload.remoteHostId.value
            # logger.debug(f"result from host: {id}")
            twins = result.payload.twins
            logger.info(f'found {len(result.payload.twins)} twins')
            feeds = list(map(lambda p: p.feed, common.flatten(map(lambda e: e.feeds, twins))))
            if len(feeds) > 0:
                logger.info(f'subscribing to {len(feeds)} feeds')
                for feed in feeds:
                    logger.info(f"subscribing to {feed.twinId.value}/{feed.id.value}")
                    stops.append(api.interest_api.fetch_interest_callback(follower_twin_id,
                                                                          twin_id=feed.twinId.value, remote_host_id=host_id,
                                                                          feed_id=feed.id.value, callback=log_feed_callback))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            for stop in stops:
                stop(timeout=0.1)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(exc)
