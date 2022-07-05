from iotics.lib.identity.api.regular_api import get_rest_identity_api

import hashlib

# this script supplements the js code that currently
# cant run because it's on an old sdk and its not running on a cors valid resolver
# check js init_iotics method


def enc(s):
    enc_s = s
    if enc_s[0] != "#":
        enc_s = f'#{enc_s}'
    if len(enc_s) > 24:
        h = int(hashlib.sha256(enc_s.encode('utf-8')).hexdigest(), 16) % 10**8
        enc_s = f'{enc_s[:15]}{h}'
    return enc_s


api = get_rest_identity_api(resolver_url="https://did.prd.iotics.com")

user_seed_str = "c7613b843119990c375fb8d4296b2da8462482a40fcdabf08cd3f99d7e43a607"
agent_seed_str = "c7613b843119990c375fb8d4296b2da8462482a40fcdabf08cd3f99d7e43a607"
# agent_name = "streaming-analytics"
agent_name = "consumer-app"
user_name = "browser-user"
user_key_name = "browser-user"
# agent_key_name = "streaming-analytics"
agent_key_name = "consumer-app"

user_seed = bytes.fromhex(user_seed_str)
agent_seed = bytes.fromhex(agent_seed_str)
agent_name = enc(agent_name)
user_name = enc(user_name)

user_identity = api.create_user_identity(
    user_seed=user_seed, user_key_name=user_key_name, user_name=user_name, override_doc=False)
user_doc = api.get_register_document(user_identity.did)

# given agent seed, create agent did key and id
agent_identity = api.create_agent_identity(
    agent_seed=agent_seed, agent_key_name=agent_key_name, agent_name=agent_name, override_doc=False)
agent_name = agent_name
agent_doc = api.get_register_document(agent_identity.did)

# create agent auth delegation if it doesn't already exist and register it in the user doc
api.user_delegates_authentication_to_agent(
    agent_registered_identity=agent_identity, user_registered_identity=user_identity)

user_doc = api.get_register_document(user_identity.did)

follower_identity = api.create_twin_identity(
    twin_seed=agent_seed, twin_key_name=agent_key_name, twin_name=agent_name, override_doc=False)
user_key_name = user_key_name

follower_doc = api.get_register_document(follower_identity.did)

api.twin_delegates_control_to_agent(twin_registered_identity=follower_identity,
                                    agent_registered_identity=agent_identity)

# did:iotics:iotUp4hDwL3GRYrvNKxyqouo1QKXEphaDfYF
follower_doc = api.get_register_document(follower_identity.did)

print(follower_doc)
