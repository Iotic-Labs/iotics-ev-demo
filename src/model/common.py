from datetime import datetime, timezone
import logging
from typing import List

from iotics.api.common_pb2 import Property, Visibility

TAG = "evdemotwins"
ON_EL = "http://www.w3id.org/urban-iot/electric"
ON_SCH = "http://schema.org"
ON_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns"
ON_RDFS = "http://www.w3.org/2000/01/rdf-schema"

logger = logging.getLogger("evdemo")


def common_properties(api, author: str, model_twin_did: str = None):
    d = datetime.now(tz=timezone.utc).isoformat()
    p = [
        api.make_property_uri('https://data.iotics.com/app#createdFrom',
                              "https://data.iotics.com/app#ByModel"),
        api.make_property_literal('https://data.iotics.com/app#createdAt',
                                  d,
                                  "dateTime"),
        api.make_property_literal('https://data.iotics.com/app#updatedAt',
                                  d,
                                  "dateTime"),
        api.make_property_string('https://data.iotics.com/app#createdBy',
                                 author),
        api.make_property_string('https://data.iotics.com/app#updatedBy',
                                 author),
        # api.make_property_bool('http://demo.iotics.com/ont/demo/isDemoTwin', # should be this
        #                        True)
        api.make_property_string('http://demo.iotics.com/ont/demo/isDemoTwin',  # this is hack
                                 "true")
    ]
    if model_twin_did is not None:
        p.append(api.make_property_uri('https://data.iotics.com/app#model',
                                       f'{model_twin_did}'))
    return p


def make_model_generic(api, twin_did: str, defined_rdf_types, colour: str, label: str = None, comment: str = None, extraProps: List[Property] = None):
    create_model_resp = api.twin_api.create_twin(twin_did)
    model_did = create_model_resp.payload.twinId.value

    logger.info(f"CHARGING STATION MODEL {model_did}")

    api.twin_api.update_twin_visibility(model_did, Visibility.PUBLIC)

    properties = common_properties(api, f'Agent:{api.id_helper.agent_name}', model_twin_did=model_did)
    properties.append(api.make_property_string(f'{ON_RDFS}#label', label))
    properties.append(api.make_property_string(f'{ON_RDFS}#comment', comment))
    properties.append(api.make_property_string('http://schema.org/name', api.id_helper.agent_name))
    properties.append(api.make_property_uri('http://data.iotics.com/public#hostAllowList',
                      'http://data.iotics.com/public#allHosts'))
    properties.append(api.make_property_uri(f'{ON_RDF}#type', 'https://data.iotics.com/app#Model'))
    properties.append(api.make_property_string('https://data.iotics.com/app#color', colour))

    if extraProps is not None:
        properties = properties + extraProps

    for rdf_type in defined_rdf_types:
        properties.append(api.make_property_uri('https://data.iotics.com/app#defines', rdf_type))

    api.twin_api.replace_twin_properties(model_did, properties)
    # update_twin_response = api.twin_api.replace_twin_properties(model_did, properties)
    # logger.debug(update_twin_response)
    return model_did
