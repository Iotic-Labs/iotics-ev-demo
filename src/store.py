from distutils.sysconfig import PREFIX
import logging
import sys
from iotics.api.common_pb2 import Scope
from iotics.api.search_pb2 import ResponseType
from model.common import ON_EL, ON_RDF

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from conf import Conf
import common
import traceback
from elasticsearch import Elasticsearch, NotFoundError
from datetime import datetime, timezone
import uuid
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PREFIXES = {
    'https://data.iotics.com/app#': "ioticsApp_",
    'http://data.iotics.com/public#': "ioticsPub_",
    'http://demo.iotics.com/ont/ev/': "ioticsOntEv_",
    'http://demo.iotics.com/ont/demo/': "ioticsOntDemo_",
    'http://data.iotics.com/iotics/': 'iotics_',
    'http://schema.org/': "schemaOrg#",
    'http://www.productontology.org/doc/': "pont_",
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': "rdf_",
    'http://www.w3.org/2000/01/rdf-schema#': "rdfs_",
    'http://www.w3id.org/urban-iot/electric#': "urbanIot_",
}

ES_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "location": {
                "type": "geo_point"
            }
        }
    }
}


logger = logging.getLogger("evdemo")


def map_key(key):
    for k in PREFIXES:
        nk = key.replace(k, PREFIXES[k])
        if nk != key:
            return nk
    return "generic_"


def rand_part(didId):
    return didId[14:].lower()


def find_index_id(prefix, twin):
    # find the model ID or if not avail return a generic index name for all twins of unknown structure
    try:
        p1 = rand_part(next(p for p in twin.properties if p.key == "https://data.iotics.com/app#model").uriValue.value)
    except:
        # return twin.id.value
        p1 = "unk"
    return f'{prefix}-{p1}'


def to_value(p):
    def has_value(x):
        return x is not None and len(x.value) > 0

    if has_value(p.stringLiteralValue):
        return p.stringLiteralValue.value
    if has_value(p.uriValue):
        return p.uriValue.value
    if has_value(p.literalValue):
        return p.literalValue.value
    if has_value(p.langLiteralValue):
        return p.langLiteralValue.value
    return ""


def find_label(twin):
    return to_value(next(p for p in twin.properties if p.key == "http://www.w3.org/2000/01/rdf-schema#label"))


def create_index(es: Elasticsearch, name):
    try:
        es.indices.get(index=name)
    except NotFoundError:
        try:
            resp = es.indices.create(index=name, body=ES_INDEX_MAPPING)
            logging.debug(resp)
        except:
            logging.error(f'could not create feed {traceback.format_exc()}')


def feed_doc(twin, feed):
    interest = feed.payload.interest
    msg_feed = interest.followedFeed.feed
    data = json.loads("{}")
    if "json" in feed.payload.feedData.mime:
        data = json.loads(feed.payload.feedData.data)

    doc = twin_doc(twin)
    doc['timestamp'] = datetime.now(timezone.utc).isoformat()
    doc['occurredAt'] = feed.payload.feedData.occurredAt.seconds
    doc['mime'] = feed.payload.feedData.mime
    doc['feed'] = msg_feed.id.value
    doc['data'] = data

    return doc


def store_feed(es, twin, sharedData):
    interest = sharedData.payload.interest
    msg_feed = interest.followedFeed.feed
    index = f'{find_index_id("feed", twin)}-{msg_feed.id.value}'
    try:
        resp = es.index(index=index, id=uuid.uuid1(), document=feed_doc(twin, sharedData))
        logging.debug(resp['result'])
    except Exception:
        logging.error(f'could not store feed {traceback.format_exc()}')


def twin_doc(twin):
    doc = {
        'twinId': twin.id.value,
        'visibility': twin.visibility,
        # geojson format (note lon at 0 and lat at 1)
        'location': {"type": "Point", "coordinates": [twin.location.lon, twin.location.lat]},
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    for p in twin.properties:
        nk = map_key(p.key)
        doc[nk] = to_value(p)
    return doc


def store_twin(es, twin):
    # sort properties by name then hash content for ID - then add timestamp
    try:
        index = find_index_id("twin", twin)
        create_index(es, index)
        resp = es.index(index=index, id=rand_part(twin.id.value), document=twin_doc(twin))

        for feedObj in twin.feeds:
            feed = feedObj.feed
            index = f'{find_index_id("feed", twin)}-{feed.id.value}'
            create_index(es, index)

        logging.debug(resp['result'])
    except Exception:
        logging.error(f'could not store feed {traceback.format_exc()}')


def find_bind_store(rdfType, follower_twin_id, es, api):
    logger.info(f'Searching for Twins of type {rdfType}')

    payload = SearchPayloadBuilder()

    properties_filter = []  # exact match
    properties_filter.append(api.make_property_uri(f'{ON_RDF}#type', rdfType))
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
            for twin in twins:
                feeds_len = len(twin.feeds)
                store_twin(es, twin)
                if feeds_len > 0:
                    logger.info(f'subscribing to {twin.id.value}/{feeds_len} feeds')
                    for fd in twin.feeds:
                        feed = fd.feed
                        logger.info(f"subscribing to {feed.twinId.value}/{feed.id.value}")
                        stops.append(api.interest_api.fetch_interest_callback(follower_twin_id,
                                                                              twin_id=feed.twinId.value, remote_host_id=host_id,
                                                                              feed_id=feed.id.value,
                                                                              # need to force capturing of twin object or else the closure
                                                                              # won't capture the current value
                                                                              callback=lambda message, tt=twin: store_feed(es, tt, message)))

    except KeyboardInterrupt:
        pass
    finally:
        try:
            for stop in stops:
                stop(timeout=0.1)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(exc)


if __name__ == '__main__':
    # read config
    conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not conf.init_and_validate() else print("")  # pylint: disable=expression-not-assigned
    # init logger
    common.init_logger()

    elasticConfFile = open(f'{str(Path.home())}/.config/elastic.json')
    elasticConf = json.load(elasticConfFile)
    defaultElasticConf = elasticConf["default"]

    es = Elasticsearch(defaultElasticConf["host"],
                       basic_auth=[defaultElasticConf["user"], defaultElasticConf["password"]],
                       verify_certs=False)

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
    follower_twin_id = common.make_or_get_follower(api)

    # check our follower twin looks like we'd hope
    common.log_description(api.twin_api.describe_twin(follower_twin_id))

    executor = ThreadPoolExecutor(os.cpu_count() * 4)

    executor.submit(find_bind_store(rdfType=f'{ON_EL}#ChargingStation',
                    follower_twin_id=follower_twin_id,
                    es=es,
                    api=api))
    # ---
    executor.submit(find_bind_store(rdfType=f'{ON_EL}#Connector',
                    follower_twin_id=follower_twin_id,
                    es=es,
                    api=api))
    # ---
    # for this program to find the forecast twins you'll need to run on demo2
    executor.submit(find_bind_store(rdfType="http://www.productontology.org/doc/Predictive_analytics",
                    follower_twin_id=follower_twin_id,
                    es=es,
                    api=api))
