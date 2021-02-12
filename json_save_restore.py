import json

import json_save_restore

""" 
    сохранение словаря в json файл.
    получение словаря из json файла.
    json удобно экранирует все спецсимволы.
"""


def save_json(data: dict, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=2)


def read_json(filename: str):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data_json = json.loads(f.read())
    except IOError:
        return None
    else:
        return data_json

