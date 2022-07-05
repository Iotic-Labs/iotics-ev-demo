from datetime import datetime
from elasticsearch import Elasticsearch
import json
from pathlib import Path


elasticConfFile = open(f'{str(Path.home())}/.config/elastic.json')
elasticConf = json.load(elasticConfFile)
defaultElasticConf = elasticConf["default"]

es = Elasticsearch(defaultElasticConf["host"],
                   basic_auth=[defaultElasticConf["user"], defaultElasticConf["password"]],
                   verify_certs=False)

doc = {
    'author': 'kimchy',
    'text': 'Elasticsearch: cool. bonsai cool.',
    'timestamp': datetime.now(),
}
resp = es.index(index="test-index", id=1, document=doc)
print(resp['result'])

resp = es.get(index="test-index", id=1)
print(resp['_source'])

es.indices.refresh(index="test-index")

resp = es.search(index="test-index", query={"match_all": {}})
print("Got %d Hits:" % resp['hits']['total']['value'])
for hit in resp['hits']['hits']:
    print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])
