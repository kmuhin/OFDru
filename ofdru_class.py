# Copyright (c) 2020 Konstantin Mukhin Al.
# Модуль для работы с ofd.ru
# https://ofd.ru/razrabotchikam

from datetime import datetime
import requests

import json_save_restore


class OfdKey:
    key: str
    file_key = 'authtoken.json'
    url_key = r'https://ofd.ru/api/Authorization/CreateAuthToken'

    def __init__(self):
        self.__date_format = '%Y-%m-%dT%H:%M:%S'
        self.key = ''
        self.ExpirationDateUtc = datetime.utcnow().strftime(self.__date_format)
        self.data = {}
        self.request = ''
        self.__headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
        }

    def __repr__(self):
        return self.key

    def update_key(self, login, password):
        self.get_key_from_file()
        if self.expired:
            self.get_key_from_url(login, password)
        self.save_key_to_file()
        return True if self.data else False

    def flush_key(self):
        """
        sets AuthToken to empty
        sets ExpirationDateUtc to now
        """
        self.key = ''
        self.ExpirationDateUtc = datetime.utcnow().strftime(self.__date_format)
        self.request = ''
        self.data = {}

    def get_key_from_file(self):
        """
        reads AuthToken from file OfdKey.file_key
        """
        # считываю токен и дату обновления из файла
        data = json_save_restore.read_json(self.file_key)
        if data:
            self.key = data.get('AuthToken')
            self.ExpirationDateUtc = data.get('ExpirationDateUtc')
            self.data = data
        else:
            self.flush_key()
        return data

    def save_key_to_file(self):
        """
        saves AuthToken to file OfdKey.file_key
        """
        if self.data:
            json_save_restore.save_json(self.data, self.file_key)

    def get_key_from_url(self, login, password):
        """
        gets AuthToken from url
        """
        json_auth = {'Login': login, 'Password': password}
        rep = requests.post(OfdKey.url_key, json=json_auth, headers=self.__headers)
        self.request = rep
        if rep.status_code == 200:
            # рассматриваю ответ как json
            data = rep.json()
        if data:
            self.key = data.get('AuthToken')
            self.ExpirationDateUtc = data.get('ExpirationDateUtc')
            self.data = data
        return data

    def format_date(self, iso_date):
        """
        returns datetime object from text using OfdKey.__date_format
        """
        return datetime.strptime(iso_date, self.__date_format)

    @property
    def expired(self):
        if self.format_date(self.ExpirationDateUtc) > datetime.utcnow():
            return False
        return True


def get_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    return requests.get(url, headers)


class OfdKkt:
    """
    authotoken - OfdKey has key and expired date
    data_kkt - dict with KKT data for requests:
        {'INN': '', 'FNumber': '', 'KKTNumber': '', 'KKTRegNumber': ''}
        INN - ИНН организации
        FNumber - номер ФН (фискальный накопитель)
        KKTNumber - заводской номер кассы
        KKTRegNumber - регистрационный номер ККТ в ФНС
    """

    def __init__(self, key, data_kkt=''):
        self.request = ''
        self.key = key
        self.data_kkt = dict(data_kkt) if data_kkt else {}
        self.last_url = ''
        self.last_json_data = ''

    def get_json_url(self, url):
        self.last_url = url
        self.request = get_url(url)
        if self.request.status_code == 200:
            self.last_json_data = self.request.json()
        else:
            self.last_json_data = ''
        return self.last_json_data

    def get_kkt_info(self):
        """
        Информация по всем ККТ.

        Возвращает список всех ККТ т.к. data содержит список.
        Из документации запрос описан так:
        https://ofd.ru/api/integration/v1/inn/{INN}/kkts?FNSerialNumber={FNumber}&KKTSerialNumber={KKTNumber}&KKTRegNumber={KKTRegNumber}&AuthToken={Code}
        06.02.2021 Проверил укороченный запрос, выдает те же данные:
        https://ofd.ru/api/integration/v1/inn/{INN}/kkts?AuthToken={Code}
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkts?FNSerialNumber={FNumber}&KKTSerialNumber={KKTNumber}&KKTRegNumber={KKTRegNumber}&AuthToken={Code}'
        url = url_template.format(**self.data_kkt, Code=self.key)
        rep = self.get_json_url(url)
        if rep:
            data = rep['Data'][0]
            self.info = data
            if not data_kkt:
                pass
        return data

    def get_receipts_short(self, date1='', date2=''):
        """
        Детальные чеки с наименованиями 'Items' за указанные период

        Период не должен превышать 30 дней.
        Возвращает чеки открытой смены.
        Возвращает чеки закрытых смен.
        """
        # ошибочный запрос из документации
        # url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/DateFrom/{Date1}/DateTo/{Date2}/receipts-with-fpd-short'
        # корректный запрос
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts-with-fpd-short?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
        date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
        date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
        url = url_template.format(**self.data_kkt, Code=self.key, Date1=date1, Date2=date2)
        rep = self.get_json_url(url)
        data = ''
        if rep:
            data = rep['Data']
        return data

    def get_receipts(self, date1='', date2=''):
        """
        Короткие чеки без наименований за указанный период

        Период не должен превышать 30 дней.
        Показывает чеки открытой смены.
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
        date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
        date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
        url = url_template.format(**self.data_kkt, Code=self.key, Date1=date1, Date2=date2)
        rep = self.get_json_url(url)
        data = ''
        if rep:
            data = rep['Data']
        return data

    def get_receipts_shift(self, shift):
        """
        Чеки за указанную смену

        Не возвращает чеки открытой смены.
        Возвращает чеки закрытых смен в короткой форме.
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipts?ShiftNumber={Shift}&FnNumber={FNumber}&AuthToken={Code}'
        url = url_template.format(**self.data_kkt, Code=self.key, Shift=shift)
        rep = self.get_json_url(url)
        if rep:
            data = rep['Data']
        return data

    def get_z_reports(self, date1='', date2=''):
        """
        z-отчеты за указанный период

        Период не должен превышать 30 дней.
        Возвращает z-отчет открытой смены, если был чек.
           Без полей 'Close_CDateUtc', 'Close_DocNumber', 'Close_DocDateTime', 'Close_DocRawId', 'ShiftDocsCount' .
        Возвращает z-отчеты закрытых смен.
        Поле 'Id', похоже, генерится рандомно при каждом запросе.
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/zreports?dateFrom={Date1}&dateTo={Date2}&AuthToken={Code}'
        date1 = date1 if date1 else datetime.now().strftime("%Y-%m-%dT00:00:01")
        date2 = date2 if date2 else datetime.now().strftime("%Y-%m-%dT23:59:59")
        url = url_template.format(**self.data_kkt, Code=self.key, Date1=date1, Date2=date2)
        rep = self.get_json_url(url)
        data = ''
        if rep:
            data = rep['Data']
        return data

    def get_receipt_by_id(self, rawid):
        """
        Детальный чек с наименованиями 'Items' по уникальному идентификатору {RawId}

        Возвращает чеки открытой смены.
        Возвращает чеки закрытых смен.
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/receipt/{RawId}?AuthToken={Code}'
        url = url_template.format(**self.data_kkt, Code=self.key, RawId=rawid)
        rep = self.get_json_url(url)
        if rep:
            data = rep['Data']
        return data

    def get_receipt_by_shift(self, shift, docshift):
        """
        Детальный чек с наименованиями 'Items' номер смены и номеру ФД за смену

        Показывает чеки открытой смены.
        """
        url_template = r'https://ofd.ru/api/integration/v1/inn/{INN}/kkt/{KKTRegNumber}/zreport/{ShiftNumber}/receipt/{DocShiftNumber}?AuthToken={Code}'
        url = url_template.format(**self.data_kkt, Code=self.key, ShiftNumber=shift, DocShiftNumber=docshift)
        rep = self.get_json_url(url)
        if rep:
            data = rep['Data']
        return data


def get_total_items_quantity(receipts):
    """
    Кол-во товара по чекам
    возвращает словарь с именами товара Item в ключах и общей суммой по Quantity
    """
    items = {}
    for item in [i for attr in receipts if attr.get('Items') for i in attr['Items']]:
        if items.get(item['Name']):
            items[item['Name']] += item['Quantity']
        else:
            items[item['Name']] = item['Quantity']
    return items


if __name__ == '__main__':
    token = OfdKey()
    config = json_save_restore.read_json('config.json')
    token.update_key(*config['auth'])
    ofd = OfdKkt(token, config['kkt'])
