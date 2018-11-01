# -*- coding: utf-8 -*-
# @Time     :  2018/7/20
# @Author   :  Cary
# @Function :
import os
import yaml
import pandas as pd


def get_config():
    try:
        BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        BASE_DIR = os.path.join(BASE_DIR, 'Digikey')
        file_path = os.path.join(BASE_DIR, 'config')
        with open(file_path) as f:
            config = yaml.load(f)
        return config
    except Exception as e:
        print(e)


def get_data_from_xlsx():
    config = get_config()
    data = pd.read_excel(config['IMPORT_FILENAME'])
    return config['IMPORT_FILENAME'][:-5], data.iloc[:, 0]
