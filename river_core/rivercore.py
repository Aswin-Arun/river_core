# See LICENSE file for details
""" Main file containing all necessary functions of river_core """
import sys
import os
import glob
import shutil
import datetime
import importlib
import configparser
import filecmp
import json

from river_core.log import *
import river_core.utils as utils
from river_core.constants import *
from river_core.__init__ import __version__
from river_core.sim_hookspecs import *
# import riscv_config.checker as riscv_config
# from riscv_config.errors import ValidationError
from envyaml import EnvYAML
from jinja2 import Template

# TODO List:
# [ ] Improve logging errors


# Misc Helper Functions
def sanitise_pytest_json(json):
    '''
        Function to sanitise pytest JSONs 

        :param json: JSON to sanitise 

        :type json: list  

        :return return_data: list  
    '''
    return_data = []
    for json_row in json:
        # NOTE: Playing with fire here, pytest developers could (potentially) change this
        if json_row.get('$report_type', None) == 'TestReport':
            return_data.append(json_row)

    return return_data


def generate_report(output_dir, gen_json_data, target_json_data, ref_json_data,
                    config, test_dict):
    '''
        Work in Progress

        Function to create an HTML report from the JSON files generated by individual plugins

        :param output_dir: Output directory for programs generated

        :param json_data: JSON data combined from Plugins 

        :param config: Config ini with the loaded by the configparser module

        :param test_list: Test List loaded as a dict 

        :type output_dir: str

        :type json_data: str

        :type config: list

        :type test_list: dict 
    '''

    #DONE:NEEL: This report is currently useless. Need pass fail results per
    #test. Why not send the test_list here and print the info

    # Filter JSON files
    gen_json_data = sanitise_pytest_json(gen_json_data)
    target_json_data = sanitise_pytest_json(target_json_data)
    ref_json_data = sanitise_pytest_json(ref_json_data)
    ## Get the proper stats about passed and failed test
    # NOTE: This is the place where you determine when your test passed fail, just add extra things to compare in the if condition if the results become to high
    num_passed = num_total = num_unav = num_failed = 0
    for test in test_dict:
        num_total = num_total + 1
        try:
            if test_dict[test]['result'] == 'Unavailable':
                num_unav = num_unav + 1
                continue
            elif test_dict[test]['result'] == 'Passed':
                num_passed = num_passed + 1
            else:
                num_failed = num_failed + 1
        except:
            logger.warning("Couldn't get a result from the Test List Dict")

    # DONE:NEEL The below should be constants in constants.py with automatic
    # absolute path detection. Please check riscof for this.
    root = os.path.abspath(os.path.dirname(__file__))
    str_report_template = root + '/templates/report.html'
    str_css_template = root + '/templates/style.css'
    report_file_name = 'report_{0}.html'.format(
        datetime.datetime.now().strftime("%Y%m%d-%H%M"))
    report_dir = output_dir + '/reports/'
    html_objects = {}
    html_objects['name'] = "RiVer Core Verification Report"
    html_objects['date'] = (datetime.datetime.now().strftime("%d-%m-%Y"))
    html_objects['time'] = (datetime.datetime.now().strftime("%H:%M"))
    html_objects['version'] = __version__
    html_objects['isa'] = config['river_core']['isa']
    html_objects['dut'] = config['river_core']['target']
    html_objects['generator'] = config['river_core']['generator']
    html_objects['reference'] = config['river_core']['reference']
    html_objects['test_dict'] = test_dict
    html_objects['target_data'] = target_json_data
    html_objects['ref_data'] = ref_json_data
    html_objects['gen_data'] = gen_json_data
    html_objects['num_passed'] = num_passed
    html_objects['num_failed'] = num_failed
    html_objects['num_unav'] = num_unav

    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    with open(str_report_template, "r") as report_template:
        template = Template(report_template.read())

    output = template.render(html_objects)

    shutil.copyfile(str_css_template, report_dir + 'style.css')

    report_file_path = report_dir + '/' + report_file_name
    with open(report_file_path, "w") as report:
        report.write(output)

    logger.info(
        'Final report saved at {0}\nMay the debugging force be with you!'.
        format(report_file_path))

    return report_file_path


def confirm():
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("Type [Y/N] to continue execution ? ").lower()
    return answer == "y"


def rivercore_clean(config_file, verbosity):
    '''
        Alpha
        Work in Progress

    '''

    config = configparser.ConfigParser()
    config.read(config_file)
    output_dir = config['river_core']['work_dir']
    logger.level(verbosity)
    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('****** Cleaning Mode ****** ')
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')

    suite = config['river_core']['generator']
    target = config['river_core']['target']
    ref = config['river_core']['reference']

    if not os.path.exists(output_dir):
        logger.info(output_dir + ' directory does not exist. Nothing to delete')
        return
    else:
        logger.info('The following directory will be removed : ' +
                    str(output_dir))
        logger.info('Hope you took a backup of the reports')
        res = confirm()
        if res:
            shutil.rmtree(output_dir)
            logger.info(output_dir + ' directory deleted')


def rivercore_generate(config_file, verbosity):
    '''
        Function to generate the assembly programs using the plugin as configured in the config.ini.

        :param config_file: Config.ini file for generation

        :param output_dir: Output directory for programs generated

        :param verbosity: Verbosity level for the framework

        :type config_file: click.Path

        :type output_dir: click.Path

        :type verbosity: str
    '''

    logger.level(verbosity)
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.debug('Read file from {0}'.format(config_file))

    output_dir = config['river_core']['work_dir']

    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Generation Mode ****** ')

    # TODO Test multiple plugin cases
    # Current implementation is using for loop, which might be a bad idea for parallel processing.

    suite_list = config['river_core']['generator'].split(',')

    logger.info(
        "The river_core is currently configured to run with following parameters"
    )
    logger.info("The Output Directory (work_dir) : {0}".format(output_dir))
    logger.info("ISA : {0}".format(config['river_core']['isa']))

    for suite in suite_list:

        # Give Plugin Info
        logger.info("Plugin Jobs : {0}".format(config[suite]['jobs']))
        logger.info("Plugin Seed : {0}".format(config[suite]['seed']))
        logger.info("Plugin Count (Times to run the test) : {0}".format(
            config[suite]['count']))
        generatorpm = pluggy.PluginManager("generator")
        generatorpm.add_hookspecs(RandomGeneratorSpec)

        path_to_module = config['river_core']['path_to_suite']
        plugin_suite = suite + '_plugin'

        # Get ISA and pass to plugin
        isa = config['river_core']['isa']
        config[suite]['isa'] = isa
        logger.info('Now loading {0} Suite'.format(suite))
        abs_location_module = path_to_module + '/' + plugin_suite + '/' + plugin_suite + '.py'
        logger.debug("Loading module from {0}".format(abs_location_module))
        # generatorpm_name = 'river_core.{0}_plugin.{0}_plugin'.format(suite)
        try:
            generatorpm_spec = importlib.util.spec_from_file_location(
                plugin_suite, abs_location_module)
            generatorpm_module = importlib.util.module_from_spec(
                generatorpm_spec)
            generatorpm_spec.loader.exec_module(generatorpm_module)
            plugin_class = "{0}_plugin".format(suite)
            class_to_call = getattr(generatorpm_module, plugin_class)
            # TODO:DOC: Naming for class in plugin
            generatorpm.register(class_to_call())

        except FileNotFoundError as txt:
            logger.error(suite + " not found at : " + path_to_module + ".\n" +
                         str(txt))
            raise SystemExit

        # DONE:NEEL: I don't like this hard-coding below. Everything should come
        # from config.ini or the names should be consistant for autodetection.

        #DONE:NEEL isa fields should not be local to plugins. They have to be
        #common for all plugins
        generatorpm.hook.pre_gen(spec_config=config[suite],
                                 output_dir='{0}/{1}'.format(output_dir, suite))
        test_list = generatorpm.hook.gen(
            gen_config='{0}/{1}_plugin/{1}_gen_config.yaml'.format(
                path_to_module, suite),
            module_dir=path_to_module,
            output_dir=output_dir)
        generatorpm.hook.post_gen(
            output_dir='{0}/{1}'.format(output_dir, suite),
            regressfile='{0}/{1}/regresslist.yaml'.format(output_dir, suite))

        test_list_file = output_dir + '/test_list.yaml'
        testfile = open(test_list_file, 'w')
        utils.yaml.dump(test_list[0], testfile)
        testfile.close()

        logger.info('Test list is generated and available at {0}'.format(
            test_list_file))


def rivercore_compile(config_file, test_list, coverage, verbosity):
    '''
        Work in Progress

        Function to compile generated assembly programs using the plugin as configured in the config.ini.

        :param config_file: Config.ini file for generation

        :param output_dir: Output directory for programs generated

        :param test_list: Test List exported from generate sub-command 

        :param coverage: Enable coverage merge and stats from the reports 

        :param verbosity: Verbosity level for the framework

        :type config_file: click.Path

        :type output_dir: click.Path

        :type test_list: click.Path

        :type verbosity: str
    '''

    logger.level(verbosity)
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.debug('Read file from {0}'.format(config_file))

    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Compilation Mode ******')

    output_dir = config['river_core']['work_dir']
    asm_gen = config['river_core']['generator']
    target_list = config['river_core']['target'].split(',')
    ref_list = config['river_core']['reference'].split(',')

    #DONE:NEEL: REPLACE ; with && to ensure failure handling
    #DONE:NEEL: Worthwhile to print some useful config values like work_dir,
    # isa, etc here as logger.info output

    logger.info(
        "The river_core is currently configured to run with following parameters"
    )
    logger.info("The Output Directory (work_dir) : {0}".format(output_dir))
    logger.info("ISA : {0}".format(config['river_core']['isa']))
    logger.info("Generator Plugin : {0}".format(asm_gen))
    logger.info("Target Plugin : {0}".format(target_list))
    logger.info("Reference Plugin : {0}".format(ref_list))

    if coverage:
        logger.info("Coverage mode is enabled")
        logger.info(
            "Just a reminder to ensrue that you have installed things with coverage enabled"
        )

    # Load coverage stats
    if coverage:
        coverage_config = config['coverage']
    else:
        coverage_config = None
    if '' in target_list:
        logger.info('No targets configured, so moving on the reference')
    else:
        for target in target_list:
            logger.info("DuT Info")
            logger.info("DuT Jobs : {0}".format(config[target]['jobs']))
            logger.info("DuT Count (Times to run) : {0}".format(
                config[target]['count']))

            dutpm = pluggy.PluginManager('dut')
            dutpm.add_hookspecs(DuTSpec)

            isa = config['river_core']['isa']
            config[target]['isa'] = isa
            path_to_module = config['river_core']['path_to_target']
            plugin_target = target + '_plugin'
            logger.info('Now running on the Target Plugins')
            logger.info('Now loading {0}-target'.format(target))

            abs_location_module = path_to_module + '/' + plugin_target + '/' + plugin_target + '.py'
            logger.debug("Loading module from {0}".format(abs_location_module))

            try:
                dutpm_spec = importlib.util.spec_from_file_location(
                    plugin_target, abs_location_module)
                dutpm_module = importlib.util.module_from_spec(dutpm_spec)
                dutpm_spec.loader.exec_module(dutpm_module)

                # DuT Plugins
                # DONE:NEEL: I don't like this hard-coding below. Everything should come
                # from config.ini or the names should be consistant for autodetection.
                # TODO:DOC: Naming for class in plugin
                plugin_class = "{0}_plugin".format(target)
                class_to_call = getattr(dutpm_module, plugin_class)
                dutpm.register(class_to_call())
            except:
                logger.error(
                    "Sorry, loading the requested plugin has failed, please check the configuration"
                )
                raise SystemExit

            dutpm.hook.init(ini_config=config[target],
                            test_list=test_list,
                            work_dir=output_dir,
                            coverage_config=coverage_config,
                            plugin_path=path_to_module)
            dutpm.hook.build()
            target_json = dutpm.hook.run(module_dir=path_to_module)

    if '' in ref_list:
        logger.info('No references, so exiting the framework')
        raise SystemExit
    else:
        for ref in ref_list:

            logger.info("Reference Info")
            logger.info("Reference Jobs : {0}".format(config[ref]['jobs']))
            logger.info("Reference Count (Times to run the test) : {0}".format(
                config[ref]['count']))
            refpm = pluggy.PluginManager('dut')
            refpm.add_hookspecs(DuTSpec)

            path_to_module = config['river_core']['path_to_ref']
            plugin_ref = ref + '_plugin'
            logger.info('Now loading {0}-target'.format(ref))
            # Get ISA from river
            isa = config['river_core']['isa']
            config[ref]['isa'] = isa

            abs_location_module = path_to_module + '/' + plugin_ref + '/' + plugin_ref + '.py'
            logger.debug("Loading module from {0}".format(abs_location_module))

            try:
                refpm_spec = importlib.util.spec_from_file_location(
                    plugin_ref, abs_location_module)
                refpm_module = importlib.util.module_from_spec(refpm_spec)
                refpm_spec.loader.exec_module(refpm_module)

                # DuT Plugins
                # DONE:NEEL: I don't like this hard-coding below. Everything should come
                # from config.ini or the names should be consistant for autodetection.
                # TODO:DOC: Naming for class in plugin
                plugin_class = "{0}_plugin".format(ref)
                class_to_call = getattr(refpm_module, plugin_class)
                refpm.register(class_to_call())
            except:
                logger.error(
                    "Sorry, requested plugin is not really was not found at location, please check config.ini"
                )
                raise SystemExit

            refpm.hook.init(ini_config=config[ref],
                            test_list=test_list,
                            work_dir=output_dir,
                            coverage_config=coverage_config,
                            plugin_path=path_to_module)
            refpm.hook.build()
            ref_json = refpm.hook.run(module_dir=path_to_module)

        ## Comparing Dumps

        result = 'Unavailable'
        test_dict = utils.load_yaml(test_list)
        for test, attr in test_dict.items():
            test_wd = attr['work_dir']
            if not os.path.isfile(test_wd + '/dut.dump'):
                logger.error('Dut dump for Test: {0} is missing'.format(test))
                continue
            if not os.path.isfile(test_wd + '/ref.dump'):
                logger.error('Ref dump for Test: {0} is missing'.format(test))
                continue
            filecmp.clear_cache()
            result = filecmp.cmp(test_wd + '/dut.dump', test_wd + '/ref.dump')
            # ASK: If we need this in the test-list as well?
            test_dict[test]['result'] = 'Passed' if result else 'Failed'
            utils.save_yaml(test_dict, test_list)
            if not result:
                logger.error(
                    "Dumps for test {0}. Do not match. TEST FAILED".format(
                        test))
            else:
                logger.info(
                    "Dumps for test {0} Match. TEST PASSED".format(test))

        # DONE:NEEL: I have replaced the below with the above. The dumps shuold
        # always be dut.dump and ref.dump. Will come back to this when multiple
        # dumps need to be checked. If you agree delete the below code.

        # Start checking things after running the commands
        # Report generation starts here
        # Target
        # Move this into a function
        if not target_json[0] or not ref_json[0]:
            logger.error(
                'JSON files not available exiting\nPossible reasons:\n1. Pytest crashed internally\n2. Log files are were not returned by the called plugin.\nI\'m sorry, no HTML reports for you :('
            )
            raise SystemExit

        json_file = open(target_json[0] + '.json', 'r')
        # NOTE Ignore first and last lines cause; Fails to load the JSON
        # target_json_list = json_file.readlines()[1:-1]
        # json_file.close()
        target_json_list = json_file.readlines()
        json_file.close()
        target_json_data = []
        for line in target_json_list:
            target_json_data.append(json.loads(line))

        json_file = open(ref_json[0] + '.json', 'r')
        # NOTE Ignore first and last lines cause; Fails to load the JSON
        # ref_json_list = json_file.readlines()[1:-1]
        # json_file.close()
        ref_json_list = json_file.readlines()
        json_file.close()
        ref_json_data = []
        for line in ref_json_list:
            ref_json_data.append(json.loads(line))

        # Need to an Gen json file for final report
        # TODO:CHECK: Only issue is that this can ideally be a wrong approach

        try:
            logger.info("Checking for a generator json to create final report")
            json_files = glob.glob(
                output_dir +
                '/.json/{0}*.json'.format(config['river_core']['generator']))
            logger.debug(
                "Detected generated JSON Files: {0}".format(json_files))

            # Can only get one file back
            gen_json_file = max(json_files, key=os.path.getctime)
            json_file = open(gen_json_file, 'r')
            target_json_list = json_file.readlines()
            json_file.close()
            gen_json_data = []
            for line in target_json_list:
                gen_json_data.append(json.loads(line))

        except:
            logger.warning("Couldn't find a generator JSON file")
            gen_json_data = []

        # See if space saver is enabled
        dutpm.hook.post_run(test_dict=test_dict, config=config)
        refpm.hook.post_run(test_dict=test_dict, config=config)

        logger.info("Now generating some good HTML reports for you")
        report_html = generate_report(output_dir, gen_json_data,
                                      target_json_data, ref_json_data, config,
                                      test_dict)

        # Check if web browser
        if utils.str_2_bool(config['river_core']['open_browser']):
            try:
                import webbrowser
                logger.info("Openning test report in web-browser")
                webbrowser.open(report_html)
            except:
                return 1


def rivercore_merge(config_file, verbosity, db_files, output_db):
    '''
        Work in Progress

        Function to merge coverage databases

        :param config_file: Config.ini file for generation

        :param verbosity: Verbosity level for the framework

        :param db_files: Tuple containing list of database files to merge
        
        :param output_db: Final output database name 

        :type config_file: click.Path

        :type verbosity: str
    '''

    logger.level(verbosity)
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.debug('Read file from {0}'.format(config_file))

    logger.info('****** RiVer Core {0} *******'.format(__version__))
    logger.info('Copyright (c) 2021, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info('****** Merge Mode ******')

    output_dir = config['river_core']['work_dir']
    target_list = config['river_core']['target'].split(',')

    # Time for reports
    # TODO Check this
    merge_time = datetime.datetime.now().strftime("%a-%-d-%b-%Y-@-%H-%M")
    logger.info(
        "The river_core is currently configured to run with following parameters"
    )
    logger.info("The Output Directory (work_dir) : {0}".format(output_dir))
    logger.info("ISA : {0}".format(config['river_core']['isa']))
    logger.info("Target Plugin : {0}".format(target_list))
    logger.info("The files it's about to merge: {0}".format(db_files))
    logger.info

    for target in target_list:
        dutpm = pluggy.PluginManager('dut')
        dutpm.add_hookspecs(DuTSpec)

        isa = config['river_core']['isa']
        config[target]['isa'] = isa
        path_to_module = config['river_core']['path_to_target']
        plugin_target = target + '_plugin'
        logger.info('Now loading {0}-target'.format(target))
        abs_location_module = path_to_module + '/' + plugin_target + '/' + plugin_target + '.py'
        logger.debug("Loading module from {0}".format(abs_location_module))

        try:
            dutpm_spec = importlib.util.spec_from_file_location(
                plugin_target, abs_location_module)
            dutpm_module = importlib.util.module_from_spec(dutpm_spec)
            dutpm_spec.loader.exec_module(dutpm_module)

            plugin_class = "{0}_plugin".format(target)
            class_to_call = getattr(dutpm_module, plugin_class)
            dutpm.register(class_to_call())
        except:
            logger.error(
                "Sorry, loading the requested plugin has failed, please check the configuration"
            )
            raise SystemExit

        dutpm.hook.merge_db(db_files=db_files,
                            config=config,
                            output_db=output_db)

        # Add link to main report file

        try:

            report_file = glob.glob(output_dir + '/reports/report_*.html')
            # TODO Check naming
            report_str = '<h3><a href={0}.html>Coverage Merge Report on {1}</h3></a>\n'.format(
                output_db, merge_time)
            html_file = open(report_file[0], 'r+')
            data = html_file.readlines()
            data.insert(-1, report_str)
            html_file.seek(0)
            html_file.writelines(data)
            html_file.close()
            logger.info(
                'Modified the final report to point at the HTML report generated by DuT Plugin'
            )
        except:

            logger.info(
                'Could not find the final report\nExiting the framework')
