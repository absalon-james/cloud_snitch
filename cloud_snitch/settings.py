import logging
import os
import sys
import yaml


LOG_LEVELS = set([
    'ERROR',
    'WARNING',
    'CRITICAL',
    'DEBUG',
    'INFO'
])

conf_filename = os.environ.get(
    'CLOUD_SNITCH_CONF_FILE',
    '/etc/cloud_snitch/cloud_snitch.yml'
)

with open(conf_filename, 'r') as f:
    conf_data = yaml.load(f.read())


ENVIRONMENT = {
    'account_number': conf_data['environment']['account_number'],
    'name': conf_data['environment']['name']
}

# Base logging
default_format = '%(name)s %(levelname)s - %(message)s'
LOG_FORMAT = conf_data.get('log_format', default_format)

# Get log level from config
default_level = 'DEBUG'
conf_level = conf_data.get('log_level', default_level)
if conf_level not in LOG_LEVELS:
    conf_level = default_level
LOG_LEVEL = logging.getLevelName(conf_level)

logger = logging.getLogger()
console_handler = logging.StreamHandler(stream=sys.stderr)
formatter = logging.Formatter(LOG_FORMAT)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(LOG_LEVEL)

# Adjust level of neo4j logging
conf_level = conf_data.get('neo4j_log_level', default_level)
if conf_level not in LOG_LEVELS:
    conf_level = default_level
conf_level = logging.getLevelName(conf_level)
neo4j_logger = logging.getLogger('neo4j')
neo4j_logger.setLevel(conf_level)


# Neo4j connections
NEO4J_USERNAME = conf_data['neo4j']['username']
NEO4J_PASSWORD = conf_data['neo4j']['password']
NEO4J_URI = conf_data['neo4j']['uri']

DATA_DIR = conf_data['data_dir']
