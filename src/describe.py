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
                         user_seed=my_conf.user_seed(),
                         user_key_name=my_conf.user_key_name,
                         user_name=my_conf.user_name,
                         agent_seed=my_conf.agent_seed(),
                         agent_key_name=my_conf.agent_key_name,
                         agent_name=my_conf.agent_name,
                         jwt_duration=20)

    my_api = ApiHelper(id_helper)

    description = my_api.twin_api.describe_twin(did="did:iotics:iotBuhdUPzfSUz7cihKPv5eSAfpmX3Wcd4WM")

    print(description)
