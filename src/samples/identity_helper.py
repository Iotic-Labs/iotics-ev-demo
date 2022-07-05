import hashlib
import logging
from datetime import timedelta

import requests
from timeloop import Timeloop

from iotics.lib.identity.api.high_level_api import get_rest_high_level_identity_api
from iotics.lib.identity.error import IdentityRegisterDocumentKeyConflictError

logger = logging.getLogger("evdemo")


class IdHelper():

    def __init__(self,
                 spacename: str,
                 user_seed: str = None,
                 user_key_name: str = None,
                 user_name: str = None,
                 agent_seed: str = None,
                 agent_key_name: str = None,
                 agent_name: str = None,
                 jwt_duration: int = 30) -> None:
        super().__init__()
        self.__user_seed = user_seed
        self.__user_key_name = user_key_name
        self.__user_name = user_name if user_name.startswith("#") else "#" + user_name
        self.__agent_seed = agent_seed
        self.__agent_key_name = agent_key_name
        self.__agent_name = agent_name if agent_name.startswith("#") else "#" + agent_name
        logger.debug(user_seed)
        logger.debug(user_key_name)
        logger.debug(user_name)
        logger.debug(agent_seed)
        logger.debug(agent_key_name)
        logger.debug(agent_name)
        self.__jwt_duration = jwt_duration
        self.__jwt_token = None

        self.__space_dns = spacename
        self.__index_url = f"https://{self.space_dns}/index.json"
        self.__index_json = requests.get(self.__index_url).json()
        self.__resolver_url = self.__index_json["resolver"]
        self.__id_api = get_rest_high_level_identity_api(resolver_url=self.__resolver_url)

        self.__user_registered_id, self.__agent_registered_id = \
            self.__id_api.create_user_and_agent_with_auth_delegation(
                user_seed=bytearray.fromhex(self.__user_seed),
                user_key_name=self.__user_key_name,
                user_name=self.__user_name,
                agent_seed=bytearray.fromhex(self.__agent_seed),
                agent_key_name=self.__agent_key_name,
                agent_name=self.__agent_name,
                delegation_name='#AuthDeleg'
            )

        self.__generate_jwt()

    def __generate_jwt(self):
        tloop = Timeloop()

        @tloop.job(interval=timedelta(seconds=(self.__jwt_duration - 2)))
        def regenerate_token():
            self.__jwt_token = \
                self.__id_api.create_agent_auth_token(
                    agent_registered_identity=self.__agent_registered_id,
                    user_did=self.__user_registered_id.did,
                    duration=self.__jwt_duration
                )
            logger.debug(f"self.jwt_token: {self.jwt_token}")

        # call it the first time, then start the timeloop job
        regenerate_token()
        tloop.start()

    def create_twin_did_and_register(self, twin_name: str, override_doc: bool = False, delegation_name="#ControlDeleg") -> str:
        twin_key_name = f'key_for_{twin_name}'
        twin_name = self.massage_twin_name(twin_name)
        twin_seed = bytes.fromhex(self.__agent_seed)
        twin_registered_identity = self.__id_api.create_twin(
            twin_seed=twin_seed, twin_key_name=twin_key_name, override_doc=override_doc)

        agent_registered_identity = self.__agent_registered_id

        try:
            self.__id_api.advanced_api.delegate_control(twin_registered_identity.key_pair_secrets,
                                                        twin_registered_identity.issuer.did,
                                                        agent_registered_identity.key_pair_secrets,
                                                        agent_registered_identity.issuer.did,
                                                        delegation_name)
        except IdentityRegisterDocumentKeyConflictError as irdce:
            logger.debug(f'exception when creating delegation: {irdce}')

        return twin_registered_identity.did

    @property
    def jwt_token(self):
        return self.__jwt_token

    @property
    def space_dns(self):
        return self.__space_dns

    @property
    def agent_registered_id(self):
        return self.__agent_registered_id

    @property
    def agent_name(self):
        return self.__agent_name

    @staticmethod
    def massage_twin_name(name):
        enc_name = name
        if enc_name[0] != "#":
            enc_name = f'#{enc_name}'
        if len(enc_name) > 24:
            h = int(hashlib.sha256(enc_name.encode('utf-8')).hexdigest(), 16) % 10**8
            enc_name = f'{enc_name[:15]}{h}'
        return enc_name
