from os.path import expanduser
import os
import sys
import getopt
import requests

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def usage(m):
    print(m)
    print("Usage:")
    print()
    print("     -h|--help")
    print("        this message")
    print()
    print("     -u|--user-seed-file=<path>")
    print("        env:IOTICS_USER_SEED_FILE, default: ~/.iotics-user-seed")
    print("        path to the user seed")
    print()
    print("     -K|--user-key-name=<name>")
    print("        env:IOTICS_UK_NAME, default: user-0")
    print("        the user key name")
    print()
    print("     -a|--agent-seed-file=<path>")
    print("        env:IOTICS_AGENT_SEED_FILE, default: ~/.iotics-agent-seed")
    print("        path to the agent seed")
    print()
    print("     -n|--agent-name=<name>")
    print("        env:IOTICS_AGENT_NAME, default: myagent")
    print("        your agent app name")
    print()
    print("     -k|--agent-key-name=<name>")
    print("        env:IOTICS_AK_NAME, default: agent-0")
    print("        the agent key name")
    print()
    print("     -e|--api-endpoint=<host:port>")
    print("        env:IOTICS_HOST_PORT")
    print("        host:port of the Iotic space api endpoint")
    print()


class Conf:
    def __init__(self, args):
        self.agent_seed_file = os.getenv("AGENT_SEED_FILE", "~/.config/.tutorial-ev-chargers.seed")
        self.user_seed_file = os.getenv("USER_SEED_FILE", "~/.iotics-user-seed")
        self.api_endpoint = os.getenv("IOTICS_HOST_PORT")
        self.resolver = None
        self.agent_name = os.getenv("IOTICS_AGENT_NAME", "#demo-agent")
        self.user_name = os.getenv("IOTICS_USER_NAME", "#demo-user")
        self.agent_key_name = os.getenv("IOTICS_AK_NAME", "demo-agent")
        self.user_key_name = os.getenv("IOTICS_UK_NAME", "demo-user")
        self.force_create_twins = os.getenv("IOTICS_FORCE_CREATE_TWINS", False)

        # the following properties configure the publisher behaviour

        # auth token have an expiry for security reasons. The longer the higher the chance
        # they can get stolen. 60s is a fair amount by default
        self.jwt_token_expiry = os.getenv("JWT_EXPIRE_SEC", 900)
        # how often to poll the upstream API for changes
        self.ev_api_poll_interval = os.getenv("EV_API_POLL_INTERVAL_SEC", 60)
        # how often to publish updates for feeds
        self.ev_updates_publish_interval = os.getenv("EV_UPDATES_PUBLISH_INTERVAL_SEC", 10)
        self.algo_updates_publish_interval = os.getenv("ALGO_UPDATES_PUBLISH_INTERVAL_SEC", 10)

        self.show_did_on_usage = None

        opt_ok = False

        opts = []
        try:
            opts, _ = getopt.getopt(args, "hDu:K:a:n:m:k:e:", [
                "help",
                "show-did",
                "user-seed-file=",
                "user-key-name=",
                "agent-seed-file=",
                "agent-name=",
                "user-name=",
                "agent-key-name=",
                "api-endpoint=",
            ])
            opt_ok = True
        except getopt.GetoptError as e:
            usage(f"{e}")
            sys.exit()

        if opt_ok:
            for opt, arg in opts:
                if opt in ("-h", "--help"):
                    usage("")
                    sys.exit()
                elif opt in ("-u", "--user-seed-file"):
                    self.user_seed_file = arg
                elif opt in ("-a", "--agent-seed-file"):
                    self.agent_seed_file = arg
                elif opt in ("-K", "--user-key-name"):
                    self.user_key_name = arg
                elif opt in ("-k", "--agent-key-name"):
                    self.agent_key_name = arg
                elif opt in ("-n", "--agent-name"):
                    self.agent_name = arg
                elif opt in ("-m", "--user-name"):
                    self.user_name = arg
                elif opt in ("-e", "--api-endpoint"):
                    self.api_endpoint = arg
                elif opt in ("-D", "--show-did"):
                    self.show_did_on_usage = True

        self.user_seed_file = os.path.abspath(expanduser(self.user_seed_file))
        self.agent_seed_file = os.path.abspath(expanduser(self.agent_seed_file))

    def discovery_api(self):
        return f"https://{self.api_endpoint}/index.json"

    def rest_api(self):
        return f"https://{self.api_endpoint}/qapi"

    def stomp_api(self):
        return f"wss://{self.api_endpoint}/ws"

    def resolver_api(self):
        return self.resolver

    def user_seed(self):
        seed = None
        with open(self.user_seed_file, 'r') as f:
            seed = f.readline()
        return seed

    def agent_seed(self):
        seed = None
        with open(self.agent_seed_file, 'r') as f:
            seed = f.readline()
        return seed

    def init_and_validate(self):
        errs = []
        if not self.agent_seed_file:
            errs.append("agent seed file missing")
        if not self.agent_key_name:
            errs.append("agent key name missing")
        if not self.agent_name:
            errs.append("agent name missing")
        if not self.user_key_name:
            errs.append("user key name missing")
        if not self.user_seed_file:
            errs.append("user seed file missing")
        if not self.api_endpoint:
            errs.append("api endpoint url missing")

        # can load agent seed
        agent_seed = None
        agent_seed_e = None
        try:
            agent_seed = self.agent_seed()
        except Exception as e:
            agent_seed_e = f'{e}'
            pass

        if not agent_seed:
            errs.append(f"unable to read agent seed file: {agent_seed_e}")

        # can load user seed
        user_seed = None
        user_seed_e = None
        try:
            user_seed = self.user_seed()
        except Exception as e:
            user_seed_e = f'{e}'
            pass

        if not user_seed:
            errs.append(f"unable to read user seed file: {user_seed_e}")

        if self.api_endpoint:
            # can get rest api
            rest_endpoint_e = None
            try:
                requests.get(self.rest_api(), verify=False)
            except requests.ConnectionError as e:
                rest_endpoint_e = f"{e}"
                pass
            if rest_endpoint_e:
                errs.append(f"check for rest api endpoint failed ({self.rest_api()}): {rest_endpoint_e}")

            # can get stomp api
            stomp_endpoint_ok = False
            try:
                requests.get(self.stomp_api().replace("wss://", "https://"), verify=False)
                stomp_endpoint_ok = True
            except requests.ConnectionError as e:
                pass
            if not stomp_endpoint_ok:
                errs.append(f"check for rest api endpoint failed: {self.stomp_api()}")

            discovery_endpoint_e = None
            try:
                resp = requests.get(self.discovery_api(), verify=False)
                rJson = resp.json()
                self.resolver = rJson["resolver"]
            except requests.ConnectionError as e:
                discovery_endpoint_e = f"Connection error: {e}"
                pass
            except Exception as e:
                discovery_endpoint_e = f"Unavailable: {e}"

            if discovery_endpoint_e:
                errs.append(f"check for discovery api endpoint failed ({self.discovery_api()}): {discovery_endpoint_e}")

        if len(errs) > 0:
            usage("")
            print("errors with supplied options")
            for e in errs:
                print(f"  * {e}")
            return False
        else:
            print("config OK:")
#            pp(vars(self))
            return True


if __name__ == '__main__':
    conf = Conf(sys.argv[1:])
    conf.inti_and_validate()
    print("")
