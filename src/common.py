import logging
import random
from iotics.api.common_pb2 import Visibility
from model.common import ON_RDFS, ON_RDF, TAG, common_properties
from samples.api_helper import ApiHelper

logger = logging.getLogger("evdemo")


def flatten(t):
    return [item for sublist in t for item in sublist]


def init_logger():
    logging.basicConfig(format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', level=logging.DEBUG)
    logging.getLogger('stomp.py').setLevel(level=logging.WARN)
    logging.getLogger('websocket').setLevel(level=logging.WARN)
    logging.getLogger('urllib3.connectionpool').setLevel(level=logging.WARN)
    logging.getLogger('timeloop').setLevel(level=logging.WARN)
    logging.getLogger('samples.api_helper').setLevel(level=logging.DEBUG)
    logging.getLogger('__main__').setLevel(level=logging.DEBUG)
    logging.getLogger("evdemo").setLevel(level=logging.DEBUG)
    logger.setLevel(level=logging.DEBUG)


def log_message(headers, response):
    return logger.debug(f'message received: {headers}: {response}')


def log_description(description):
    logger.info("")
    logger.info(f"Twin did ({description.payload.twin.id.value})")
    visibility_text = "PRIVATE" if description.payload.twin.visibility == Visibility.PRIVATE else "PUBLIC"
    logger.info(f"    visibility = ({visibility_text})")
    logger.info(
        f"      location = (lat: {description.payload.result.location.lat}, lon: {description.payload.result.location.lon})")
    logger.info(f"  properties # = ({len(description.payload.result.properties)})")
    for prop in description.payload.result.properties:
        logger.info(f"               | {prop.key}")
        logger.info(f"                 {as_value(prop)}")
    logger.info(f"         feeds = ({list(map(lambda p: p.feedId.value, description.payload.result.feeds))})")


def make_or_get_follower(api: ApiHelper) -> str:
    logger.info("creating follower...")
    # we make the follower with the same name of "this" agent
    follower_did = api.id_helper.create_twin_did_and_register(api.id_helper.agent_name)

    api.twin_api.create_twin(follower_did)
    logger.info(f"FOLLOWER {follower_did}")

    api.twin_api.update_twin_visibility(follower_did, Visibility.PUBLIC)

    properties = common_properties(api, f'Agent:{api.id_helper.agent_name}')
    properties.append(api.make_property_string(f'{ON_RDFS}#label', f'Agent {api.id_helper.agent_name}'))
    properties.append(api.make_property_string(f'{ON_RDFS}#comment',
                                               f'Twin of application {api.id_helper.agent_name} {TAG}'))
    properties.append(api.make_property_string('http://schema.org/name', api.id_helper.agent_name))
    properties.append(api.make_property_uri('http://data.iotics.com/public#hostAllowList',
                                            'http://data.iotics.com/public#allHosts'))
    properties.append(api.make_property_uri(f'{ON_RDF}#type', 'http://www.productontology.org/doc/Application'))

    api.twin_api.replace_twin_properties(follower_did, properties)
    # update_twin_response = api.twin_api.replace_twin_properties(follower_did, properties)
    # logger.debug(update_twin_response)
    return follower_did


def as_value(prop):  # pylint:disable=inconsistent-return-statements
    if prop.literalValue.value != '':
        return prop.literalValue.value
    if prop.stringLiteralValue.value != '':
        return prop.stringLiteralValue.value
    if prop.langLiteralValue.value != '':
        return prop.langLiteralValue.value
    if prop.uriValue.value != '':
        return prop.uriValue.value
