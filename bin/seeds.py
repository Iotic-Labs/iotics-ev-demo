#!/usr/bin/python

import sys
import os
import getopt
from iotics.lib.identity.register.rest_resolver import get_rest_resolver_client
from iotics.lib.identity.api.advanced_api import AdvancedIdentityRegisterApi
from iotics.lib.identity.api.regular_api import IdentityApi
from pathlib import Path


def usage(m):
    print("Seed utility - (c) Iotic Labs 2020")
    print()
    print(m)
    print()

    print("seed.py [-n|--new] [-f|--force] [-m|--from-mnemonics=<mnemonics words>] [-o|--output-file=<path>]")
    print()
    print(" -n|--new")
    print("     creates a new seed. If --output-file is specified with a path to a file, it attempts to store the seed in the file.")
    print("     If the file specified with --output-file already exists, the command fails unless the --force option is specified.")
    print("     When creating a new seed, a set of mnemonic words are printed in output.")
    print("     The user must store these words safely because they are **the only** mechanism to retrieve the seed if it gets lost.")
    print()
    print(" -f|--force")
    print("     if specified, overrides the content of the seed in the file specified with --output-file")
    print()
    print(" -m|--from-mnemonics")
    print("     generates the seed from the mnemonics. the words must be separated by space and supplied within quotes")
    print("     For example -m\"word1 word2 word3 ...\"")
    print()
    print(" -o|--output-file")
    print("     path to the file where to store the seed. The file parent directory must exist and be writable.")
    print()
    print(" -i|--input-file")
    print("     path to the file with a seed. Reads the file and generates the mnemonics for the seed in it.")
    print()
    print()

    sys.exit()


def main(argv):
    new_seed_len = 256
    make_new = False
    force = False
    mnemonics = None
    outputfilepath = None
    inputfilepath = None

    try:
        opts, args = getopt.getopt(argv, "nfm:o:i:", ["new", "force", "from-mnemonics=", "output=", "input="])
    except getopt.GetoptError:
        usage("invalid options specified")

    for opt, arg in opts:
        if opt in ("-n", "--new"):
            make_new = True
        elif opt in ("-f", "--force"):
            force = True
        elif opt in ("-o", "--output-file"):
            outputfilepath = os.path.abspath(arg)
        elif opt in ("-i", "--input-file"):
            inputfilepath = arg
        elif opt in ("-m", "--from-mnemonics"):
            mnemonics = arg

    if not make_new and not mnemonics and not inputfilepath:
        usage(m="you must specify one of --input-file, --new or --from-mnemonics")

    seed = ""
    new_seed_mnemonics = None

    resolver_client = get_rest_resolver_client(RESOLVER, 60)
    advanced_api = AdvancedIdentityRegisterApi(resolver_client=resolver_client)
    identity_api = IdentityApi(advanced_api=advanced_api)

    inputfile = None
    if inputfilepath:
        if make_new or mnemonics or outputfilepath:
            usage("you can't specify any other option with --input-file")

        inputfile = Path(inputfilepath)
        try:
            with open(inputfile, 'r') as f:
                seed = f.readline()
                new_seed_mnemonics = Identifier.seed_to_mnemonic(seed)
                print(f"Input file: {inputfilepath}")

        except Exception as e:
            usage(f'unable to read input file {inputfilepath}: {e}')
    else:
        outputfile = None
        if outputfilepath:
            outputfile = Path(outputfilepath)
            if not force and outputfile.exists():
                usage(m="output file exists. Use --force to overwrite its content")

        if make_new and mnemonics:
            usage(m="you can't specify both --new and --from-mnemonics")

        if make_new and not mnemonics:
            seed = Identifier.new_seed(new_seed_len)
            new_seed_mnemonics = Identifier.seed_to_mnemonic(seed)
        if not make_new and mnemonics:
            seed = Identifier.mnemonic_to_seed(mnemonics, lang="english")
            new_seed_mnemonics = mnemonics

        if outputfile:
            try:
                with open(outputfile, 'w') as f:
                    f.write(seed)
                    print(f"Output file: {outputfilepath}")
            except Exception as e:
                usage(f'unable to write to specified file {outputfilepath}: {e}')

    print(f'Seed: {seed}')
    print(f'Mnemonics: {new_seed_mnemonics}')


if __name__ == '__main__':
    main(sys.argv[1:])
