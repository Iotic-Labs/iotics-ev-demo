import traceback
import logging
import sys
from iotics.api.common_pb2 import Scope, GeoCircle, GeoLocation
from iotics.api.search_pb2 import ResponseType
from model.common import ON_EL, ON_RDF

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper, SearchPayloadBuilder
from conf import Conf
import common
from elasticsearch import Elasticsearch, NotFoundError
from datetime import datetime, timezone
import uuid
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ES_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "location": {
                "type": "geo_point"
            }
        }
    }
}

LONDON = GeoCircle(radiusKm=25, location=GeoLocation(lat=51.509865, lon=-0.118092))

logger = logging.getLogger("evdemo")


MODELS_MAP = {

}


def map_key(key):
    return key


def rand_part(didId):
    return didId[14:].lower()


def property_value_of(twin, key):
    # find the model ID or if not avail return a generic index name for all twins of unknown structure
    try:
        return next(p for p in twin.properties if p.key == key).uriValue.value

    except:
        # return twin.id.value
        return None


def label_of(twin):
    return property_value_of(twin, "http://www.w3.org/2000/01/rdf-schema#label")


def model_did_of(twin):
    return property_value_of(twin, "https://data.iotics.com/app#model")


def index_for(twin):
    did = model_did_of(twin)
    if did is None:
        return "unk"
    return rand_part(did)


def make_index_name(*args):
    i = '-'.join(args)
    return f'{i}-{datetime.now().strftime("%y%m%d")}'.lower()


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


def create_index(es: Elasticsearch, index_name):
    try:
        es.indices.get(index=index_name)
    except NotFoundError:
        try:
            resp = es.indices.create(index=index_name, body=ES_INDEX_MAPPING)
            logging.debug(resp)
        except Exception:  # pylint: disable=broad-except
            logging.error(f'could not create feed {traceback.format_exc()}')


def store_search_meta(meta):
    meta["timestamp"] = datetime.now(timezone.utc).isoformat()
    index = make_index_name("meta", "search")
    create_index(es=es, index_name=index)
    es.index(index=index, id=uuid.uuid1(), document=meta)
    logging.info(meta)


def feed_doc(twin, model_label, feed):
    interest = feed.payload.interest
    msg_feed = interest.followedFeed.feed
    data = json.loads("{}")
    if "json" in feed.payload.feedData.mime:
        data = json.loads(feed.payload.feedData.data)

    doc = twin_doc(twin, model_label)
    doc['timestamp'] = datetime.now(timezone.utc).isoformat()
    doc['occurredAt'] = feed.payload.feedData.occurredAt.seconds
    doc['mime'] = feed.payload.feedData.mime
    doc['feed'] = msg_feed.id.value
    doc['data'] = data

    return doc


def store_feed(es, twin, model_label, sharedData):
    interest = sharedData.payload.interest
    msg_feed = interest.followedFeed.feed
    index = make_index_name("feed", index_for(twin), msg_feed.id.value)
    try:
        doc = feed_doc(twin, model_label, sharedData)
        logging.info(f'feed_doc: {doc}')
        resp = es.index(index=index, id=uuid.uuid1(), document=doc)
        logging.debug(resp['result'])
    except Exception:  # pylint: disable=broad-except
        logging.error(f'could not store feed {traceback.format_exc()}')


def twin_doc(twin, model_label):
    doc = {
        'twinId': twin.id.value,
        'visibility': twin.visibility,
        # geojson format (note lon at 0 and lat at 1)
        'location': {"type": "Point", "coordinates": [twin.location.lon, twin.location.lat]},
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'model_label': model_label
    }
    for p in twin.properties:
        nk = map_key(p.key)
        v = to_value(p)
        if nk in doc:
            what = doc[nk]
            if isinstance(what, list):
                what.append(v)
                doc[nk] = what
            else:
                doc[nk] = [what, v]
        else:
            doc[nk] = v
    return doc


def store_twin(es, twin, model_label):
    # sort properties by name then hash content for ID - then add timestamp
    twin_index = index_for(twin)
    try:
        index = make_index_name("twin", twin_index)
        create_index(es, index)
        doc = twin_doc(twin, model_label)
        logging.info(f'twin_doc: {doc}')
        resp = es.index(index=index, id=rand_part(twin.id.value), document=doc)

        for feedObj in twin.feeds:
            feed = feedObj.feed
            index = make_index_name("feed", twin_index, feed.id.value)
            create_index(es, index)

        # logging.debug(resp['result'])
    except Exception:  # pylint: disable=broad-except
        logging.error(f'could not store feed {traceback.format_exc()}')

def load_models():
    query = '''
    PREFIX iotics_app: <https://data.iotics.com/app#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?id ?label WHERE {
        ?id a iotics_app:Model .
        ?id rdfs:label ?label
    }'''

    response = api.meta_api.sparql(query=query)
    for host_id in response:
        payload=response[host_id]
        for b in payload['results']['bindings']:
            id = b['id']['value']
            label = b['label']['value']
            MODELS_MAP[id] = label

def model_label_of(twin):
    try:
        model_did = model_did_of(twin)
        if model_did in MODELS_MAP:
            return MODELS_MAP[model_did]
    except:
        pass
    return None

def find_bind_store(follower_id, es, api, rdfType=None, ioticsModel=None, location=None):
    logger.info(f'Searching for Twins of type {rdfType}')

    payload = SearchPayloadBuilder()
    search_meta = {}

    properties_filter = []
    if rdfType is not None:
        properties_filter.append(api.make_property_uri(f'{ON_RDF}#type', rdfType))
        search_meta["rdf_type"] = rdfType
    if ioticsModel is not None:
        properties_filter.append(api.make_property_uri(f'https://data.iotics.com/app#model', ioticsModel))
        search_meta["model"] = ioticsModel
    if len(properties_filter) > 0:
        payload.properties = properties_filter

    if location is not None:
        payload.location = location
        search_meta["location"] = {"type": "Point", "coordinates": [location.location.lon, location.location.lat]}
        search_meta["radiusKm"] = location.radiusKm

    payload.response_type = ResponseType.FULL

    request = payload.build()
    result_stream = api.search_api.dispatch_search_request(request,
                                                           client_ref=ApiHelper.randClientRef(),
                                                           scope=Scope.GLOBAL,
                                                           timeout=5)

    subscribed_feeds = []
    i = 0
    max_feeds = 0

    search_meta["total_hosts"] = 0
    search_meta["total_twins"] = 0
    for result in api.search_api.process_results_stream(result_stream):
        host_id = None if result.payload.remoteHostId.value == '' else result.payload.remoteHostId.value
        # logger.debug(f"result from host: {id}")
        twins = result.payload.twins
        logger.info(f'found < {len(result.payload.twins)} > twins in host {host_id}')
        search_meta["total_hosts"] = search_meta["total_hosts"] + 1
        search_meta["total_twins"] = search_meta["total_twins"] + len(result.payload.twins)
        for twin in twins:
            feeds_len = len(twin.feeds)
            model_label = model_label_of(twin=twin)
            store_twin(es, twin, model_label)

            if feeds_len > 0:
                logger.info(f'found < {feeds_len} > feeds in {twin.id.value}')
                max_feeds = max_feeds + feeds_len
                for fd in twin.feeds:
                    i = i + 1
                    feed = fd.feed
                    subscribed_feeds.append({
                        'feed_n': i,
                        'follower': follower_id,
                        'twin_id': feed.twinId.value,
                        'twin': twin,
                        'model_label': model_label,
                        'feed_id': feed.id.value,
                        'remote_host_id': host_id,
                    })

    search_meta["total_feeds"] = max_feeds
    store_search_meta(meta=search_meta)
    stops = []
    try:
        for sub_feed in subscribed_feeds:
            logger.info(
                f"subscription {sub_feed['feed_n']}/{max_feeds}: {sub_feed['twin_id']}/{sub_feed['feed_id']}")
            twin = sub_feed['twin']
            model_label = sub_feed['model_label']
            s_future = api.interest_api.fetch_interest_callback(sub_feed['follower'],
                                                                twin_id=sub_feed['twin_id'],
                                                                remote_host_id=sub_feed['remote_host_id'],
                                                                feed_id=sub_feed['feed_id'],
                                                                # need to force capturing of twin object or else the closure
                                                                # won't capture the current value
                                                                callback=lambda message, ml=model_label, tt=twin:
                                                                    store_feed(
                                                                        es=es, twin=tt, model_label=ml, sharedData=message
                                                                    )
                                                                )
            # time.sleep(0.05)
            stops.append(s_future)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            for stop in stops:
                stop(timeout=0.1)
        except Exception:  # pylint: disable=broad-except
            logger.error(f'"exception handling subscription" {traceback.format_exc()}')


if __name__ == '__main__':
    # read config
    conf = Conf(sys.argv[1:])
    # validate config
    sys.exit() if not conf.init_and_validate() else print("")  # pylint: disable=expression-not-assigned
    # init logger
    common.init_logger()
    logging.getLogger('elastic_transport.transport').setLevel(level=logging.WARN)
    logging.getLogger('root').setLevel(level=logging.WARN)

    elasticConfFile = open(f'{str(Path.home())}/.config/elastic.json')
    elasticConf = json.load(elasticConfFile)
    defaultElasticConf = elasticConf["default"]

    es = Elasticsearch(defaultElasticConf["host"],
                       basic_auth=[defaultElasticConf["user"], defaultElasticConf["password"]],
                       verify_certs=False)

    # make auth facade
    id_helper = IdHelper(conf.api_endpoint,
                         resolver_url=conf.resolver_api(),
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

    executor = ThreadPoolExecutor(os.cpu_count() * 4)

    load_models()

    # executor.submit(find_bind_store(location=LONDON,
    #                                 follower_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))

    # executor.submit(find_bind_store(rdfType=f'{ON_EL}#ChargingStation',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))
    # # ---
    # executor.submit(find_bind_store(rdfType=f'{ON_EL}#Connector',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))

    ## london buses
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iot9uyhTtK5R3imardFgj2HW684vrSdgFZwb',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotX3p2m5J4R1NK3FYsoJ687NhsB7hbtFbio',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotUQDmmfJe6iSy6mVMXLumodeuVoqE7HQY9',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotVaxnGGHryhQ2k7xwddoqYcKLA8ktBWHQg',
    #                                 follower_twin_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))

    # vessels
    executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotAGq33aYjExKNnnajfticKV1eyv8c37niW',
                                    follower_id=follower_twin_id,
                                    es=es,
                                    api=api))
    # # Hydrogen Tank Model
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotHhib6Bb49kttpPyL8PRRs5fjKS6N6b4Sb',
    #                                 follower_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))

    # # PorticoMeteoHelixSensor
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotWxa9oGf792MdfS8ZwFoafSG6D1LanA8wH',
    #                                 follower_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))
    # # PorticoAirQualitySensorA
    # executor.submit(find_bind_store(ioticsModel=f'did:iotics:iotNRisUqWL8yLdzskmHJ2vNRdZkgUitgcnD',
    #                                 follower_id=follower_twin_id,
    #                                 es=es,
    #                                 api=api))


