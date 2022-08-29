#!/usr/bin/env python3

# Read & write configuration files and provide default values.
#
# Licensed under the terms of the GPL2, see LICENSE file.
# Copyright (c) 2022 Julian Heinzel <jeinzi@gmx.de>

import os
import copy
import json


configFilePath = "config.json"

defaultConfig = {
    "inputPath": "",
    "outputPath": "result.gpgl",
    "gerbvPath": {
        "posix": "gerbv",
        "nt": "C:/Program Files (x86)/gerbv-2.6.0/bin/gerbv.exe"
    },
    "ghostscriptPath": {
        "posix": "gs",
        "nt": "C:/Program Files/gs/gs9.56.1/bin/gswin64.exe"
    },
    "pstoeditPath": {
        "posix": "pstoedit",
        "nt": "C:/Program Files/pstoedit/pstoedit.exe"
    },
    "offset": [0.5,0.5],
    "border": [1,1],
    "matrix": [1,0,0,1],
    "speed": [2,2],
    "force": [12,40],
    "cutMode": 0,
    "deviceName": {
        "posix": "/dev/usb/lp0",
        "nt": "\\\\[Computer Name]\\[Shared Name]"
    }
}




def getDefaultConfig():
    """Create a configuration object for a chosen operating system.

    Returns:
        dict: A dictionary containing configuration key/value pairs.
    """
    config = copy.deepcopy(defaultConfig)
    for key, value in config.items():
        if type(value) is dict:
            config[key] = value[os.name]
    return config




def readConfigFile(path):
    """Read and parse the config file as a dictionary.

    Args:
        path (string, optional): The path to the configuration file.

    Returns:
        dict: The config file as a dictionary.
    """
    config = {}
    try:
        with open(path) as configFile:
            config = json.load(configFile)
    except FileNotFoundError as e:
        print(f"Configuration file '{e.filename}' can't be found.")
    except json.decoder.JSONDecodeError:
        print(f"Can't decode configuration file '{path}'.")
        exit()
    return config




def writeConfigFile(config, path=configFilePath):
    """Dump config object to file.

    Args:
        config (dict): Config key/value pairs.
        path (string, optional): Path to the config file.
                                 Defaults to internal default value.
    """
    # The string replacements are just there to remove unnecessary
    # trailing zeros, to improve readability.
    jsonString = json.dumps(config, indent=4).replace(".0,", ",").replace(".0\n", "\n")
    with open(path, "w") as file:
        file.write(jsonString)




def getConfig(path=configFilePath):
    """Get configuration settings from file with fallback to default values.

    Args:
        path (string, optional): The path to the config file.
                                 Defaults to internal default value.

    Returns:
        dict: Configuration settings.
    """
    config = getDefaultConfig()
    fileConfig = readConfigFile(path)
    # Use values from config file where defined, otherwise use default values.
    config.update(fileConfig)
    return config
