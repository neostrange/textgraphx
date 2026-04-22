from neo4j import GraphDatabase
import os
import sys
import getopt
import logging
from textgraphx.config import get_config

# module logger
logger = logging.getLogger(__name__)

help_message = '-u <neo4j username> -p <password> -s <source directory> -b <bolt uri>'

neo4j_user = 'neo4j'
neo4j_password = 'password'
source_dataset_path = ''
uri = 'bolt://localhost:7687'


class GraphDBBase():
    def __init__(self, command=None, argv=None, extended_options='', extended_long_options=[]):
        self.uri = None
        self.neo4j_user = None
        self.neo4j_password = None
        self.source_dataset_path = None
        self.opts = {}
        self.args = []

        if argv:
            self.__get_main_parameters__(command=command, argv=argv, extended_options=extended_options,
                                         extended_long_options=extended_long_options)

        cfg = get_config()

        # allow command-line or explicit overrides to take precedence
        uri = self.uri or os.getenv('NEO4J_URI') or cfg.neo4j.uri or 'bolt://localhost:7687'
        user = self.neo4j_user or os.getenv('NEO4J_USER') or cfg.neo4j.user or 'neo4j'
        password = self.neo4j_password or os.getenv('NEO4J_PASSWORD') or cfg.neo4j.password or 'password'

        # Pass through any driver-specific options defined in a repo-local
        # config.ini under [neo4j] if present. We try to read textgraphx/config.ini
        # for compatibility with older deployments.
        other_params = {}
        try:
            import configparser
            config_file = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
            cp = configparser.ConfigParser()
            cp.read(config_file)
            if 'neo4j' in cp:
                for k, v in cp['neo4j'].items():
                    if k in ('uri', 'user', 'password'):
                        continue
                    # simple converters for common keys
                    if k == 'encrypted':
                        other_params[k] = bool(int(v))
                    else:
                        other_params[k] = v
        except Exception:
            # if config isn't present just continue with defaults
            pass

        self._driver = GraphDatabase.driver(uri, auth=(user, password), **other_params)
        self._session = None
        logger.info("GraphDBBase initialized for uri=%s user=%s", uri, user)

    def get_opts(self):
        return self.opts

    def get_option(self, options: list, default = None):
        for opt, arg in self.opts:
            if opt in options:
                return arg

        return default

    def close(self):
        self._driver.close()

    def get_session(self):
        return self._driver.session()

    def execute_without_exception(self, query: str):
        try:
            self.get_session().run(query)
        except Exception as e:
            pass

    def executeNoException(self, session, query: str):
        try:
            session.run(query)
        except Exception as e:
            pass

    def __get_main_parameters__(self, command, argv, extended_options='', extended_long_options=[]):
        try:
            self.opts, self.args = getopt.getopt(argv, 'hu:p:s:b:' + extended_options,
                                       ['help', 'neo4j-user=', 'neo4j-password=', 'source-path=',
                                        'bolt='] + extended_long_options)
        except getopt.GetoptError as e:
            logger.exception("Error parsing command line options: %s", e)
            logger.info("%s %s", command, help_message)
            sys.exit(2)
        for opt, arg in self.opts:
            if opt == '-h':
                logger.info("%s %s", command, help_message)
                sys.exit()
            elif opt in ("-u", "--neo4j-user"):
                self.neo4j_user = arg
            elif opt in ("-p", "--neo4j-password"):
                self.neo4j_password = arg
            elif opt in ("-s", "--source-path"):
                self.source_dataset_path = arg
            elif opt in ("-b", "--bolt"):
                self.uri = arg
