# Copyright (c) 2020 Konstantin Mukhin Al.
# Тестовый Модуль для отладки работы с API ofd.ru
# Прототип для модуля с классами ofdru_class.py
# https://ofd.ru/razrabotchikam

from datetime import datetime
import requests
import logging

from ofd_config import data_auth, data_kkt
import json_save_restore

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.

import http.client as http_client

http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


def get_json_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    rep = requests.get(url, headers)
    rep_data = ''
    if rep.status_code == 200:
        rep_data = rep.json()
    return rep_data


def get_authtoken(login, password):
    """
    получаю токен для авторизации
    data_auth = [login, password]
    """
    # нужно ли обновлять токен
    is_refresh_authtoken = True
    # файл с ключем авторизации в формате json
    file_authtoken = 'authtoken.json'
    url_authtoken = r'http://127.0.0.1:8000/cgi-bin/http_server_test.py'
    url_authtoken = r'https://ofd.ru/api/Authorization/CreateAuthToken'
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    # считываю ключ авторизации и дату обновления из файла
    rep_data = json_save_restore.read_json(file_authtoken)
    rep_data_date = ''
    if rep_data:
        rep_data_date = datetime.strptime(rep_data['ExpirationDateUtc'], '%Y-%m-%dT%H:%M:%S')
        print('cache token time expiration:', rep_data_date)
        print(datetime.utcnow())
        # в файле так же лежит время жизни ключа в UTC
        # проверяю актуальность ключа
        if datetime.utcnow() < rep_data_date:
            is_refresh_authtoken = False
    # получаю или обновляю ключ
    if is_refresh_authtoken:
        # посылаю логин и пароль, получаю токен
        json_auth = {'Login': login, 'Password': password}
        rep = requests.post(url_authtoken, json=json_auth, headers=headers)
        # рассматриваю ответ как json
        rep_data = rep.json()
        # сохраняю полученные данные с токеном в файл в формате json
        if rep_data:
            json_save_restore.save_json(rep_data, file_authtoken)
            rep_data_date = datetime.strptime(rep_data['ExpirationDateUtc'], '%Y-%m-%dT%H:%M:%S')
    print(rep_data)
    print('time expiration:', rep_data_date)
    print('time now:', datetime.utcnow())
    return rep_data['AuthToken']


def get_kkt_info(data_kkt, authtoken):
    """
    Информация по всем ККТ.

    Возвращает список всех ККТ т.к. data содержит список.
    Из документации запрос такой:
    https://ofd.ru/api/integration/v1/inn/{INN}/kkts?FNSerialNumber={FNumber}&KKTSerialNumber={KKTNumber}&KKTRegNumber={KKTRegNumber}&AuthToken={Code}
    06.02.2021 Проверил укороченный запрос, выдает те же данные
    https://ofd.ru/api/integration/v1/inn/{INN}/kkts?AuthToken={Code}
    """
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkts?FNSerialNumber={FNumber}&KKTSerialNumber={KKTNumber}&KKTRegNumber={KKTRegNumber}&AuthToken={Code}'
    url = url_template.format(**data_kkt, Code=authtoken)
    return get_json_url(url)


def get_receipts_short(data_kkt, authtoken, date1='', date2=''):
    """
    Детальные чеки с наименованиями 'Items' за указанные период

    Период не более 30 дней.
    Возвращает чеки открытой смены.
    Возвращает чеки закрытых смен.
    """
    # ошибочный запрос из документации
    # url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/DateFrom/{Date1}/DateTo/{Date2}/receipts-with-fpd-short'
    # корректный запрос
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts-with-fpd-short?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
    date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
    date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
    url = url_template.format(**data_kkt, Date1=date1, Date2=date2, Code=authtoken)
    return get_json_url(url)


def get_receipts(data_kkt, authtoken, date1='', date2=''):
    """
    Короткие чеки без наименований за указанный период

    Период не должен превышать 30 дней.
    Показывает чеки открытой смены.
    """

    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
    date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
    date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
    url = url_template.format(**data_kkt, Date1=date1, Date2=date2, Code=authtoken)
    return get_json_url(url)


def get_receipts_shift(shift, data_kkt, authtoken):
    """
    Чеки за указанную смену

    Не возвращает чеки открытой смены.
    Возвращает чеки закрытых смен в короткой форме.
    """
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts?ShiftNumber={Shift}&FnNumber={FNumber}&AuthToken={Code}'
    url = url_template.format(**data_kkt, Code=authtoken, Shift=shift)
    return get_json_url(url)


def get_z_reports(data_kkt, authtoken, date1='', date2=''):
    """
    z-отчеты за указанный период

    Период не должен превышать 30 дней.
    Возвращает z-отчет открытой смены, если был чек,
        без полей 'Close_CDateUtc', 'Close_DocNumber', 'Close_DocDateTime', 'Close_DocRawId', 'ShiftDocsCount' .
    Возвращает z-отчеты закрытых смен.
    Поле 'Id', похоже, генерится рандомно при каждом запросе.
    """
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/zreports?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
    date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
    date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
    url = url_template.format(**data_kkt, Date1=date1, Date2=date2, Code=authtoken)
    return get_json_url(url)


def get_receipt_by_id(data_kkt, authtoken, rawid):
    """
    Детальный чек с наименованиями 'Items' по уникальному идентификатору {RawId}

    Возвращает чеки открытой смены.
    Возвращает чеки закрытых смен.
    """
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipt/{RawId}?AuthToken={Code}'
    url = url_template.format(**data_kkt, RawId=rawid, Code=authtoken)
    return get_json_url(url)


def get_receipt_by_shift(data_kkt, authtoken, shift, docshift):
    """
    Детальный чек с наименованиями 'Items' номер смены и номеру ФД за смену

    Показывает чеки открытой смены.
    """
    url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/zreport/{ShiftNumber}/receipt/{DocShiftNumber}?AuthToken={Code}'
    url = url_template.format(**data_kkt, ShiftNumber=shift, DocShiftNumber=docshift, Code=authtoken)
    return get_json_url(url)


if __name__ == '__main__':
    authtoken = get_authtoken(*data_auth)
