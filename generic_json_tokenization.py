#!/usr/bin/env python
"""Tokenization script to find and replace ."""
__author__ = "Soumabha Sarkar"
__version__ = "1.0.2"
__maintainer__ = "Soumabha Sarkar"
__email__ = "soumabhasarkar@gmail.com"

import sys
import argparse
import errno
import os, fnmatch
import csv
import ast
import json
import traceback
import subprocess
import itertools

db_details_dict_keys = ['oltpDbName','cfgDbName','hostOltp','hostCfg']

def getTokenForFile(filepath, inculde_filetype_dict, exculde_filetype_dict):
    final_include_tokens = []
    try:
        # Get all include & exclude file or file type 
        inculde_filetype_list = inculde_filetype_dict.keys()
        exculde_filetype_list = exculde_filetype_dict.keys()

        # Filter include & exclude file or file type based on the file name
        filename_inculde_filetype_keys = [filetype for filetype in inculde_filetype_list if fnmatch.fnmatch( filepath, '*'+filetype)]
        filename_exculde_filetype_keys = [filetype for filetype in exculde_filetype_list if fnmatch.fnmatch( filepath, '*'+filetype)]

        include_tokens = []
        exculde_tokens = []

        # Get tokens for filtered include & exclude file or file type
        for item in filename_inculde_filetype_keys:
            include_tokens = include_tokens + inculde_filetype_dict[item]

        for item in filename_exculde_filetype_keys:
            exculde_tokens = exculde_tokens + exculde_filelist_dict[item]

        # Remove tokens for exclude files
        final_include_tokens = [token for token in include_tokens if token not in exculde_tokens]

        # Remove duplicate tokens
        final_include_tokens.sort()
        final_include_tokens = list(final_include_tokens for final_include_tokens,_ in itertools.groupby(final_include_tokens))
        
    except Exception as ex:
        print('Error occured while getting token information for {0}'.format(filepath))
        print(traceback.print_exc(file=sys.stdout))
        sys.exit(1)
    return final_include_tokens

def findReplace(directory, inculde_filetype_dict, exculde_filetype_dict):
    outputlst = []
    
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in files:
            filepath = os.path.join(path, filename)
            new_file = True
            final_include_tokens = getTokenForFile(filepath, inculde_filetype_dict, exculde_filetype_dict)
         
            if final_include_tokens:                
                for token in final_include_tokens:                    
                    out_str = ''
                    try:
                        findstr = token[0]
                        replacestr = token[1]
                        find_found = False
                        printstr = ''
                        with open(filepath, "r", encoding='ISO-8859-1') as f:
                            s = f.readlines()
                            for item in s:
                                if item.find(findstr) > -1:
                                    find_found = True
                                out_str += item.replace(findstr, replacestr)
                        if find_found:
                            with open(
                                    filepath,
                                    "w",
                                    encoding='ISO-8859-1',
                                    errors='ignore') as f:
                                outputlst.append(filepath)
                                if new_file:
                                    print('Modifying {0}'.format(filepath))
                                    new_file = False
                                print('Original String ====%s==== Replace with ====%s====' %(findstr, replacestr))
                                f.write(out_str)                                
                    except Exception as ex:
                        print('Error: Cannot replace {0} with {1} in {2} file'.format(findstr, replacestr, filepath))
                        print(traceback.print_exc(file=sys.stdout))                        
                        pass
    return outputlst

def getDbHostDbService(reader, host_env):
    db_detail = dict.fromkeys(db_details_dict_keys)
    try:
        # Get DB details in JSON file
        db_dict = reader['db_dict']     
        host_db = reader['host_db']        

        # check if there is any DB Host suffix defined for Hosting Environment
        if host_env in host_db.keys():
            host_oltp = host_db[host_env][0]
            host_cfg = host_db[host_env][1]
        else:
            host_oltp = host_db['seed'][0]  
            host_cfg = host_db['seed'][1]

        # Get DB Service name according to Environment
        oltp_db_name = db_dict[host_env] + reader['db_type']['type'][0]
        cfg_db_name = db_dict[host_env] + reader['db_type']['type'][1]
        
        db_detail['oltpDbName'] = oltp_db_name
        db_detail['cfgDbName'] =  cfg_db_name
        db_detail['hostOltp'] = host_oltp
        db_detail['hostCfg'] = host_cfg
        
    except IndexError:
        print('Error: Array out of Index ')
        print(traceback.print_exc(file=sys.stdout))
        print('DB Host suffix not found. Terminating process ')
        sys.exit(1)
        
    except ValueError:
        print("Error: Decoding JSON failed")
        print(traceback.print_exc(file=sys.stdout))
        print('DB Service name not found. Terminating process ')
        sys.exit(1)
        
    except Exception as ex:
        print("Error: Unhandled exception occured ")
        print(traceback.print_exc(file=sys.stdout))
        print('Terminating process ')
        sys.exit(1)
        
    return db_detail

def getFileList(token, node):                            
    try:
        filetype_list = token[node]
    except:
        filetype_list = []
    return filetype_list

    
def tokenize(jsonfilepath, host_env, host_reg, host_tier):    
    fileExist = os.path.exists(jsonfilepath)
    if not fileExist:
        print("The JSON file \"{0}\" does not exists. Process terminated".format(jsonfilepath))
        sys.exit(errno.ENOENT)
    with open(jsonfilepath, 'r') as jsonfile:
        try:
            reader = json.load(jsonfile)
        except ValueError:
            print('{} is not a valid json file'.format(jsonfilepath))
            print(traceback.print_exc(file=sys.stdout))
            sys.exit(errno.EBFONT)
            
        DbHostDbService = getDbHostDbService(reader,host_env)

        include_files_dict = {}
        exculde_files_dict = {}
        
        for token in reader['tokenize']['tokens']:
            try:                
                replacestr=''            
                pattern = token['pattern']    # Check if Replace Token follows a pattern                              
                if pattern:
                    findstr = token['find']
                    replacestr = token['replace'].replace('$HOST_REGION$', host_reg).replace(
                        '$HOST_ENV$', host_env).replace(
                            '$OLTP_DB_NAME$', DbHostDbService['oltpDbName'].lower()).replace(        # Replace OLTP DB Service Name
                                '$CFG_DB_NAME$',DbHostDbService['cfgDbName'].lower()).replace(       # Replace CFG DB Service Name
                                    '$HOST_OLTP$',DbHostDbService['hostOltp'].lower()).replace(      # Replace OLTP DB Host suffix
                                        '$HOST_CFG$', DbHostDbService['hostCfg'].lower()).replace(   # Replace CFG DB Host suffix
                                            '$HOST_TIER$',host_tier.upper())               
                                                               
                else:
                    findstr = token['find']
                    replacestr = token[host_tier]      #Replace string follows no pattern. Replace string value varies according to Deployment Environment                 
                                
                include_file_list = getFileList(token, 'includeFiles')
                exculde_file_list = getFileList(token, 'excludeFiles')

                for include_file in include_file_list :
                    include_files_dict.setdefault(include_file,[]).append([findstr,replacestr])     # Filter Tokens by Include File type

                for exculde_file in exculde_file_list:
                    exculde_files_dict.setdefault(exculde_file,[]).append([findstr,replacestr])     # Filter Tokens by Exclude File type
            except:
                print('Error:')
                print(traceback.print_exc(file=sys.stdout))
                sys.exit(1)                
        
        output = findReplace('.', include_files_dict, exculde_files_dict)
        if output:
            print('Total {0} files modified'.format(len(output)))            
        print(
            "==================================================================\n"
        )                                                            

def xstr(s):
    return '' if s is None else str(s)

class TokenizationArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('Error: %s\n' % message)
        self.print_help()
        sys.exit(errno.EINVAL)

def main():
    parser = TokenizationArgumentParser(
        description='This Script will replace DB URLs and other service URLs mentioned in JSON file depending on Deployment Env and Region')
    parser.add_argument(
        '-c', '--config', action='store', dest='jsonFilePath', required= True, help='JSON File path')
    parser.add_argument(
        '-r', '--region', action='store', dest='region', required= True, help='host region e.g. ie1, de1')
    parser.add_argument(
        '-e', '--environment', action='store', dest='environment', required= True, help='host env e.g. dev1, dev2, qa1')
    parser.add_argument(
        '-t','--tier', action='store', dest='tier', required= True, help='deploy tier e.g. dev, qa, prod')

    results = parser.parse_args()

    print ('Hosting Environment name: {0} \nHosting Tier: {1} \nRegion: {2} \nJSON file path: {3}'.format(
        results.environment, results.tier, results.region, results.jsonFilePath))
        
    host_reg = xstr(results.region).lower()
    host_env = xstr(results.environment).lower()
    host_tier = xstr(results.tier).lower()
    json_filepath = results.jsonFilePath
      

    print('===================Tokenization Starts======================')
    tokenize(json_filepath, host_env, host_reg, host_tier)   
    print('===================Tokenization Ends======================')


if __name__ == "__main__":
    main()
