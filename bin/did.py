#!/usr/bin/python

import sys
import os
import getopt
from iotic.lib.identity import Identifier, Document
from pathlib import Path


def usage(m):
    print("DiD utility - (c) Iotic Labs 2020")
    print()
    print(m)
    print()

    print("did.py [-s|--seed-file] [-k|--key-name] [-t|--type]")
    print()
    print(" -h|--help")
    print("     this message")
    print()
    print(" -t|--type")
    print("     document type ('user' or 'agent')")
    print()
    print(" -k|--key-name")
    print("     key name.")
    print()
    print(" -s|--seed-file")
    print("     path to the file with a seed")
    print()
    print()

    sys.exit()


def main(argv):
    seedfilepath = "~/.iotics-user-seed"
    doctype = "user"
    keyname = "user-tutorial"

    try:
        opts, args = getopt.getopt(argv, "t:k:s:", ["type=", "key-name=", "seed-file="])
    except getopt.GetoptError:
        usage("invalid options specified")

    for opt, arg in opts:
        if opt in ("-t", "--type"):
            doctype = arg
        elif opt in ("-k", "--key-name"):
            keyname = arg
        elif opt in ("-s", "--seed-file"):
            seedfilepath = arg
        elif opt in ("-h", "--help"):
            usage()
        else:
            usage()

    if not seedfilepath and not doctype and not keyname:
        usage(m="you must specify --type --key-name --seed-file")

    seedfilepath = os.path.expanduser(seedfilepath)
    seedfile = Path(seedfilepath)

    if not seedfile.exists():
        usage(m=f"seed file '{seedfilepath}' doesn't exist")

    if doctype == "user":
        doctype = Identifier.DIDType.USER
    elif doctype == "agent":
        doctype = Identifier.DIDType.AGENT
    else:
        usage(m=f"invalid type '{doctype}': must be either 'user' or 'agent'")

    seed = None
    with open(seedfile, 'r') as f:
        seed = f.readline()
    seed = Identifier.seed_to_master(seed)

    doc = create_did(doctype, seed, keyname)

    did = doc[0].id
    pk0 = doc[0].public_keys[0]

    print(did)
    print(f"   pk.size              = {doc[1].key_size}")
    print(f"   pk[0].id             = {pk0.id}")
    print(f"   pk[0].type           = {pk0.type}")
    print(f"   pk[0].public_baseb58 = {pk0.public_base58}")
    print(f"   pk[0].revoked        = {pk0.revoked}")


def create_did(did_type, seed, key_name):
    # todo should be get_or_create_did
    if isinstance(key_name, int):
        private_key_hex = Identifier.new_private_hex_from_path(seed, did_type, key_name)
    else:
        private_key_hex = Identifier.new_private_hex_from_path_str(seed, did_type, str(key_name))

    private_key_ecdsa = Identifier.private_hex_to_ECDSA(private_key_hex)

    # (todo now) if doc doesn't already exist, create new else fetch and return existing (Resolver.discover and try/catch)
    # (todo future) Check with Tim make sure key still exists in the document ? what would you do?

    doc = Document.new_did_document(did_type, private_key_ecdsa)
    # print(f'Generated DID: "{did_type}/{key}" with ID "{doc.id}"')

    return doc, private_key_ecdsa


if __name__ == '__main__':
    main(sys.argv[1:])
