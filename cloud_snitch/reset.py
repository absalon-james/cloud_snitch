"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import logging
import runs
import pprint

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    foundruns = runs.find_runs()
    for run in foundruns:
        run.run_data['status'] = 'finished'
        if 'synced' in run.run_data:
            del run.run_data['synced']
        run._save_data()
        run.update()
        logger.info('Resetting run {}'.format(run.path))
        logger.info(pprint.pformat(run.run_data))
