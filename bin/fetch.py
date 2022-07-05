#!/usr/bin/python

import sys
import os
import getopt
import datetime
from iotic.lib.identity import Identifier, Resolver
from pathlib import Path
from pprint import pprint as pp


def usage(m):
    print("DiD fetch - (c) Iotic Labs 2020")
    print()
    print(m)
    print()

    print("did.py [-s|--seed-file] [-k|--key-name] [-t|--type]")
    print()
    print(" -h|--help")
    print("     this message")
    print()
    print(" -t|--type")
    print("     document type ('user', 'agent', 'twin')")
    print()
    print(" -k|--key-name")
    print("     the key name")
    print()
    print(" -r|--resolver")
    print("     the resolver endpoint")
    print()
    print(" -s|--seed-file")
    print("     path to the file with a seed")
    print()
    print()

    sys.exit()


def main(argv):
    seedfilepath = "~/.iotics-user-seed"
    doctype = "user"
    keyname = "user-0"
    resolver = "did.stg.iotics.com"

    try:
        opts, args = getopt.getopt(argv, "t:k:s:r:", ["type=", "key-name=", "seed-file=", "resolver="])
    except getopt.GetoptError:
        usage("invalid options specified")

    for opt, arg in opts:
        if opt in ("-t", "--type"):
            doctype = arg
        elif opt in ("-s", "--seed-file"):
            seedfilepath = arg
        elif opt in ("-r", "--resolver"):
            resolver = arg
        elif opt in ("-k", "--key-name"):
            keyname = arg
        elif opt in ("-h", "--help"):
            usage()
        else:
            usage()

    if not seedfilepath and not doctype:
        usage(m="you must specify --type and --seed-file")

    if not resolver.startswith("https://"):
        resolver = f"https://{resolver}"
    seedfilepath = os.path.expanduser(seedfilepath)
    seedfile = Path(seedfilepath)

    os.environ["RESOLVER"] = resolver

    if not seedfile.exists():
        usage(m=f"seed file '{seedfilepath}' doesn't exist")

    if doctype == "user":
        doctype = Identifier.DIDType.USER
    elif doctype == "agent":
        doctype = Identifier.DIDType.AGENT
    elif doctype == "twin":
        doctype = Identifier.DIDType.TWIN
    else:
        usage(m=f"invalid type '{doctype}': must be either 'user' 'twin' or 'agent'")

    seed = None
    with open(seedfile, 'r') as f:
        seed = f.readline()
    seed = Identifier.seed_to_master(seed)

    private_key_hex = Identifier.new_private_hex_from_path_str(seed, doctype, keyname)
    private_key_ecdsa = Identifier.private_hex_to_ECDSA(private_key_hex)

    public_key_ecdsa = Identifier.private_ECDSA_to_public_ECDSA(private_key_ecdsa)
    public_key_hex = Identifier.public_ECDSA_to_bytes(public_key_ecdsa).hex()
    id = Identifier.make_identifier(public_key_hex)
    doc = Resolver.discover(id)

    print(f"Attributes")
    print(f" id = {doc.id}")
    print(f" revoked = {doc.revoked}")
    print(f" controller = {doc.controller}")
    print(f" creator = {doc.creator}")
    print(f" type = {doc.did_type}")
    print(f" update time = {datetime.datetime.fromtimestamp(doc.update_time/1000).strftime('%Y-%m-%dT%H:%M:%S.%f')}")
    print(f"Metadata")
    print(f" url = {doc.metadata.url}")
    print(f" label = {doc.metadata.label}")
    print(f" comment = {doc.metadata.comment}")
    print(f"Public keys")
    if len(doc.public_keys) == 0:
        print(" ---")
    for key in range(len(doc.public_keys)):
        pk = doc.public_keys[key]
        print(f" [{key}]")
        print(f"   id = {pk.id}")
        print(f"   revoked = {pk.revoked}")
        print(f"   type = {pk.type}")
        print(f"   public (base58) = {pk.public_base58}")
    print(f"Delegate authentications")
    if len(doc.delegate_authentication) == 0:
        print(" ---")
    for key in range(len(doc.delegate_authentication)):
        da = doc.delegate_authentication[key]
        print(f" [{key}]")
        print(f"   id = {da.id}")
        print(f"   revoked = {da.revoked}")
        print(f"   controller = {da.controller}")
    print(f"Delegate control")
    if len(doc.delegate_control) == 0:
        print(" ---")
    for key in range(len(doc.delegate_control)):
        da = doc.delegate_authentication[key]
        print(f" [{key}]")
        print(f"   id = {da.id}")
        print(f"   revoked = {da.revoked}")
        print(f"   controller = {da.controller}")


if __name__ == '__main__':
    main(sys.argv[1:])
