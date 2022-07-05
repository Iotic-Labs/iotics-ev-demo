import sys

from conf import Conf
import common
from elasticsearch import Elasticsearch
import json
from pathlib import Path

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
    l = es.indices.get(index="twin*")
    for i in l:
        es.indices.delete(index=i)
    l = es.indices.get(index="feed*")
    for i in l:
        es.indices.delete(index=i)
