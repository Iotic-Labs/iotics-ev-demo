import json
import logging
import sys

from conf import Conf
import common

from pprint import pprint as pp

import base64

from samples.identity_helper import IdHelper
from samples.api_helper import ApiHelper


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
                         resolver_url=my_conf.resolver_api(),
                         user_seed=my_conf.user_seed(),
                         user_key_name=my_conf.user_key_name,
                         user_name=my_conf.user_name,
                         agent_seed=my_conf.agent_seed(),
                         agent_key_name=my_conf.agent_key_name,
                         agent_name=my_conf.agent_name,
                         jwt_duration=my_conf.jwt_token_expiry)

    my_api = ApiHelper(id_helper)

    query = '''
    PREFIX iotics_app: <https://data.iotics.com/app#>
    SELECT ?s WHERE {
        ?s a iotics_app:Model
    }'''

    query = '''
    PREFIX iotics_app: <https://data.iotics.com/app#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?id ?label WHERE {
        ?id a iotics_app:Model .
        ?id rdfs:label ?label
    }'''

    response = my_api.meta_api.sparql(query=query)

    for host_id in response:
        payload=response[host_id]
        for b in payload['results']['bindings']:
            id = b['id']['value']
            label = b['label']['value']
            print(f'{host_id} -- {id}: {label}')
    # pp(response)
