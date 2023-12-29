import json
import scipy
import iapws
import sys
import os
import csv
import xlwt
import logging
import glob


from SAM_flatJSON.SamBaseClass import SamBaseClass
from supported_params import SUPPORTED_PARAMS

import numpy as np

from pathlib import Path
from APMonitor.apm import *
from datetime import datetime


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#    def __init__(self,
#                  CSP = 'pvwattsv7',
#                  financial = 'lcoefcr',
#                  desalination =  'RO',
#                  json_value_filepath = None,
#                  desal_json_value_filepath = None,
#                  cost_json_value_filepath = None,
#                  timestamp = str(datetime.now())
#                  ):

## TODO: update files in the filepath, OR
## update sam base class to accept JSON instead
## of opening files. 

## helper methods
#
financial_model_dict = {
    "pvwattsv7": 'lcoefcr',
    "SC_FPC": 'lcoh_calculator',
    "SC_ETC": 'lcoh_calculator',
    "linear_fresnel_dsg_iph": 'iph_to_lcoefcr',
    "trough_physical_process_heat": 'iph_to_lcoefcr',
}

def update_JSON(user_params):
    ''' update json files with any user parameters supplied (that are supported)
    via the API '''
    # TODO: handle weather file (download the user-supplied file). The path to the 
    # file should then be written to map-data.json
    base_path = "./SAM_flatJSON/defaults/"

    solar = user_params['solar_model']
    wind = user_params['wind_model']
    desal = user_params['desalination_model']
    cryst = user_params['crystallization_model']
    cost = financial_model_dict[user_params['solar_model']]

    value_files = [f'{solar}_{cost}.json', # Solar model input file
                   f'{wind}.json', # Wind model input file
                        f'{desal}.json',        # Desal model input file
                        f'{cryst}.json',        # Crystallizer model input file
                        f'{desal}_cost.json']   # Desal cost mode input file



    # TODO: integrate this with value_files
    value_file_paths = {
        'json_value_filepath':f'/tmp/{solar}_{cost}.json',
        'json_wind_value_filepath': f'/tmp/{wind}.json',
        'desal_json_value_filepath':f'/tmp/{desal}.json',
        'cost_json_value_filepath':f'/tmp/{desal}_cost.json',
        'cryst_json_value_filepath':f'/tmp/{cryst}.json'

    }
    # Update 4 input files
    # output files to /tmp for lambda system
    for input_file in value_files:
        with open(base_path + input_file, 'r') as f:
            data = json.load(f)
        # Update variable if provided
        for var in SUPPORTED_PARAMS[input_file]:
            if var in user_params.keys():
                data[var] = user_params[var]
        with open(f'/tmp/{input_file}', 'w') as f:
            json.dump(data, f)


    return value_file_paths
            


def run_models(params, json_paths):
    '''run the desal model based on user selection. For now, just running RO
    TODO: add logic to create the model based on user selection. '''
    
    # use SamBaseClass to run the models

        # def __init__(self,
        #          solar = 'pvwattsv7',
        #          financial = 'lcoefcr',
        #          desalination =  'RO',
        #          cryst = None,
        #          json_value_filepath = None,
        #          desal_json_value_filepath = None,
        #          cost_json_value_filepath = None,
        #          cryst_json_value_filepath = None,
        #          timestamp = '',
        #          ):
        
    time = datetime.now()
    print('print timestr', time)
    timestr = f'{time.year}-{time.month}-{time.day}-{time.hour}-{time.minute}-{time.second}'
    sam = SamBaseClass(
        desalination=params['desalination_model'],
        solar=params['solar_model'],
        wind=params['wind_model'],
        cryst = params['crystallization_model'] if params['crystallization_model'] else None,
        financial=params['financial_model'],
        json_value_filepath = json_paths['json_value_filepath'],
        desal_json_value_filepath = json_paths['desal_json_value_filepath'],
        cost_json_value_filepath = json_paths['cost_json_value_filepath'],
        cryst_json_value_filepath = json_paths['cryst_json_value_filepath'],
        timestamp = timestr,
    )
    # sam.desal_design(desal=params['desalination_model'])
    # run the models
    try:
        sam.main()
    except Exception as e:
        logging.error('Error running models!')
        logging.info(e)
        return (-1,)

    return (1, timestr)

def collate_outputs(time_string):
    ''' combine extracts from  output files for return to user '''
    # file_list = glob.glob(f'/tmp/CSV/*{time_string}*') + glob.glob(f'/tmp/results/*{time_string}*')
    file_list = glob.glob(f'/tmp/results/*{time_string}*.json')
    results = []
    if len(file_list) > 0:
        # pull out just the the results, for now including everything
        for json_file in file_list:
            logger.debug(f'combining resutls from {json_file}')
            with open(json_file, 'r') as f:
                results.extend(json.load(f))

    return results

        
         
def parse_parameters(inputs):
    ''' parse out the models from the input request '''
    logging.info(inputs.keys())
    if not 'solar_model' in inputs.keys():
        if 'queryStringParameters' in inputs.keys():
            inputs = inputs.get('queryStringParameters')

    logging.debug(inputs)
    

    results = {}
    results['solar_model'] = inputs.get('solar_model')
    results["wind_model"] = inputs.get('wind_model')
    results['desalination_model'] = inputs.get('desalination_model')
    results['crystallization_model'] = inputs.get('crystallization_model')
    # results['financial_model'] = inputs.get('financial_model')
    results['weather_file'] = inputs.get('weather_file')
    logging.debug(results)

    if results['solar_model']:
        results['financial_model'] = financial_model_dict[results['solar_model']]

    results['weather_file']

    if not (results.get('solar_model')):
        results['status'] = 'solar_model is required input parameters!'
        return results
    if not (results.get('desalination_model') or results.get('crystallization_model')):
        results['status'] = 'at least one of desalination_model or crystallization_model is required!'
        return results        
    
    # update json files
    json_file_paths = update_JSON(inputs)

    print(results)
    print(json_file_paths)
    print('here')
    run_results = run_models(results, json_file_paths)

    if run_results[0] > 0:
        results['model_error'] = False
        results['json'] = collate_outputs(run_results[1])

    else: 
        results['model_error'] = True
        return results

    return results


def handler(event, context):
    # TODO implement
    # logging.debug(event)
    response = {
}
    
    result = parse_parameters(event)
    if result['model_error']:
        return {
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'statusCode': 500,
            'body': json.dumps(result)
        }
    else:
        return {
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'statusCode': 200, 
            'body': json.dumps(result)
        }

if __name__=='__main__':
    with open('model_selection_test.json', 'r') as input:
        event = json.load(input)
    logging.debug(event)
    handler(event, {})