# See LICENSE for details
"""Console script for river_core."""

import click
import os

from river_core.log import *
from river_core.rivercore import rivercore_clean, rivercore_compile, rivercore_generate, rivercore_merge, rivercore_setup
from river_core.__init__ import __version__
import river_core.constants as constants


def check_config():
    """ Checks if 
    1. ~/river_core.ini\n
    2. (pwd)/river_core.ini exists
    """
    if os.path.exists(os.path.expanduser('~/river_core.ini')):
        logger.info('Loading config from ~/river_core.ini')
        return '~/river_core.ini'
    elif os.path.isfile(str(os.getcwd()) + '/river_core.ini'):
        logger.info('Loading config from current directory')
        return str(os.getcwd()) + '/river_core.ini'
    else:
        logger.error("Couldn't find config file anywhere. Exiting")
        raise SystemExit


@click.group()
@click.version_option(version=__version__)
def cli():
    """RiVer Core Verification Framework"""


@click.version_option(version=__version__)
@click.option('-v',
              '--verbosity',
              default='info',
              help='Set the verbosity level for the framework')
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False, exists=True),
    help=
    'Read option defaults from the INI file\nAuto detects river_core.ini in current directory or in the ~ directory'
)
@cli.command()
def clean(config, verbosity):
    '''
        subcommand to clean generated programs.
    '''
    logger.info(constants.header_temp.format(__version__))
    if not config:
        config = check_config()
    rivercore_clean(config, verbosity)


# -------------------------


@click.version_option(version=__version__)
@click.option(
    '--config',
    is_flag=True,
    default=None,
    help=
    'Create a sample config with the name river_core.ini in the current directory'
)
@click.option(
    '--dut',
    default=None,
    help=
    'Create a sample DuT Plugin with the specified name in the current directory'
)
@click.option(
    '--gen',
    default=None,
    help=
    'Create a sample Generator Plugin with the specified name in the current directory'
)
@click.option(
    '--ref',
    default=None,
    help=
    'Create a sample Reference Plugin with the specified name in the current directory'
)
@click.option('-v',
              '--verbosity',
              default='info',
              help='Set the verbosity level for the framework')
@cli.command()
def setup(config, dut, gen, ref, verbosity):
    '''
        subcommand to generate template setup files
    '''
    logger.info(constants.header_temp.format(__version__))

    rivercore_setup(config, dut, gen, ref, verbosity)


# -------------------------


@click.version_option(version=__version__)
@click.option('-v',
              '--verbosity',
              default='info',
              help='Set the verbosity level for the framework')
@click.option('-t',
              '--test_list',
              type=click.Path(dir_okay=False, exists=True),
              help='Test List file to pass',
              required=True)
# required=True)
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False, exists=True),
    help=
    'Read option defaults from the INI file\nAuto detects river_core.ini in current directory or in the ~ directory'
)
@click.option(
    '--dut_stage',
    type=click.Choice(['init', 'build', 'run', 'auto'], case_sensitive=False),
    default='auto',
    help=
    'Stages to run on configured DuT Plugin\n1. `init`: Call the intial setup API for the DuT plugin\n2. `build`: Call the intial setup API and build API to generate the necessary binaries for the DuT Plugin\n3. `run`: Call the intial setup API, build API and run API to initialize, generate and the run the binaries\n4.`auto` will enable run automatically and determine the other valid values [default]\n'
)
@click.option(
    '--ref_stage',
    type=click.Choice(['init', 'build', 'run', 'auto'], case_sensitive=False),
    default='auto',
    help=
    'Stages to run on configured reference Plugin\n1. `init`: Call the intial setup API for the Reference plugin\n2. `build`: Call the intial setup API and build API to generate the necessary binaries for the Reference Plugin\n3. `run`: Call the intial setup API, build API and run API to initialize, generate and the run the binaries\n4. `auto` will enable run automatically and set other valid values [default]\n'
)
@click.option(
    '--compare/--no-compare',
    default=True,
    help=
    'Toggle comparison between logs generated by the DuT and the Reference Plugin'
)
@click.option(
    '--coverage',
    is_flag=True,
    help='Enable collection of coverage statistics from the DuT plugin')
@cli.command()
def compile(config, test_list, coverage, verbosity, dut_stage, ref_stage,
            compare):
    '''
        subcommand to compile generated programs.
    '''
    logger.info(constants.header_temp.format(__version__))
    if not config:
        config = check_config()
    # Checking if the flags are ok
    if dut_stage == 'auto':
        logger.info('Auto mode detected for DuT Plugin')
        if ref_stage == 'auto':
            logger.info('Auto mode detected for Ref Plugin')
            dut_stage = 'run'
            ref_stage = 'run'
        else:
            logger.debug('Auto mode has disabled DuT Plugin')
            dut_stage = None
            if compare:
                logger.warning(
                    'Compare is enabled\nThis will be generating incomplete reports'
                )
    else:
        if ref_stage == 'auto':
            logger.debug('Auto mode has disabled Ref Plugin')
            ref_stage = None
            if compare:
                logger.warning(
                    'Compare is enabled\nThis will be generating incomplete reports'
                )
    rivercore_compile(config, test_list, coverage, verbosity, dut_stage,
                      ref_stage, compare)


@click.version_option(version=__version__)
@click.option('-v',
              '--verbosity',
              default='info',
              help='Set the verbosity level for the framework')
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False, exists=True),
    help=
    'Read option defaults from the INI file\nAuto detects river_core.ini in current directory or in the ~ directory'
)
@cli.command()
def generate(config, verbosity):
    """
    subcommand to generate programs.
    """
    logger.info(constants.header_temp.format(__version__))
    if not config:
        config = check_config()
    rivercore_generate(config, verbosity)


@click.version_option(version=__version__)
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False, exists=True),
    help=
    'Read option defaults from the INI file\nAuto detects river_core.ini in current directory or in the ~ directory'
)
@click.option('-v',
              '--verbosity',
              default='info',
              help='set the verbosity level for the framework')
@click.argument('db_files', nargs=-1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@cli.command()
def merge(verbosity, db_files, output, config):
    """
    subcommand to merge coverage databases.
    """
    logger.info(constants.header_temp.format(__version__))
    if not config:
        config = check_config()
    rivercore_merge(verbosity, db_files, output, config)


if __name__ == '__main__':
    cli()
