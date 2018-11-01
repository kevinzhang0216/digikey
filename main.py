# -*- coding: utf-8 -*-
# @Time     :  2018/7/19
# @Author   :  Cary
# @Function :
import re
import time

import requests
from bs4 import BeautifulSoup
import pandas as pd

from user_agents import UserAgent
from utils import get_data_from_xlsx


s = requests.Session()


def has_numbers(string):
    try:
        return any(char.isdigit() for char in string)
    except Exception:
        return -1


def get_item(item):
    item['Part Type'] = ' '
    item['Schematic Part'] = ''
    item['PCB Footprint'] = 'new_part'
    item['Value'] = ' '
    item['Manufacturer'] = ' '
    item['Description'] = ' '
    item['Operating Temperature'] = ' '
    item['Package / Case'] = ' '
    item['Mounting Type'] = ' '
    item['Supplier Device Package'] = ' '
    item['是否检查'] = 'FALSE'
    item['是否缺货'] = ' '
    item[u'手册链接'] = ' '
    item['Unit Price'] = ' '
    for i in range(1, 11):
        item['重要参数'+str(i)] = ' '
    return item


def parse(url, keyword):
    ua = UserAgent()
    pre_url = 'https://www.digikey.com'
    headers = {'User-Agent': ua.get_user_agent()}  # 得到随机User-Agent头
    try:
        body = s.get(url, headers=headers).content
        soup = BeautifulSoup(body, 'lxml')
        item = {}
        item = get_item(item)
        item['Manufacturer Part Number'] = keyword
        short_supply_flag = False
        current_keyword = ""
        minimum_quantity = 0 
        unit_price_USD = None
        # 两个个临时变量，保存缺货时的状态
        temp_minimum_quantity = minimum_quantity
        temp_unit_price_USD = unit_price_USD
        temp_fit_flag = False

        try:
            trs = soup.find('tbody', id='lnkPart').find_all('tr')
            for tr in trs:
                tds = tr.find_all('td')
                current_keyword = tds[4].find('span').text
                new_url = pre_url+tds[4].find('a').get('href')
                try:
                    quantity_available = int(re.sub('\D+', "", tds[7].find_all('span')[0].text.strip()))
                except Exception:
                    quantity_available = 0
                if quantity_available != 0 and current_keyword == keyword:
                    short_supply_flag = True
                unit_price_USD = tds[8].text.strip()
                try:
                    minimum_quantity = int(re.sub('\D+', "", tds[9].text.strip()))
                except Exception:
                    minimum_quantity = 0
                if current_keyword == keyword:
                    temp_fit_flag = True
                if current_keyword == keyword and quantity_available != 0:  # 如果有货且名称正确  则为正常
                    print("正常型", url) #test1 待修改
                    item['是否检查'] = 'FALSE'
                    item['备注'] = ' '
                    item['是否缺货'] = ' '
                    return parse_detail(new_url, item, headers)					
            #    if quantity_available != 0 and has_numbers(unit_price_USD)\
            #            and minimum_quantity == 1 and current_keyword == keyword:  # 当前判定条件
            #        print("正常型", url)
            #        item['是否检查'] = ' '
            #        item['备注'] = ' '
            #        item['是否缺货'] = ' '
            #        return parse_detail(new_url, item, headers)
            #    if quantity_available != 0 and has_numbers(unit_price_USD)\
            #            and minimum_quantity == 0 and current_keyword == keyword:  # 当前判定条件
            #        print("正常型", url)
            #        item['是否检查'] = ' '
            #        item['备注'] = ' '
            #        item['是否缺货'] = ' '
            #        return parse_detail(new_url, item, headers)
            #    if minimum_quantity == 1 and has_numbers(unit_price_USD): #
            #        temp_minimum_quantity = minimum_quantity
            #        temp_unit_price_USD = unit_price_USD
            if (short_supply_flag == False and temp_fit_flag == True):  # 名称正确 但是缺货
                print("缺货", url)
                item[u'是否缺货'] = '缺货'
                item['是否检查'] = 'FALSE'
                item['备注'] = ' '
                return parse_detail(new_url, item, headers)
            if temp_fit_flag == False:    #名称不正确
                print("错误类型Error器件名不完整:", url)
                item[u'备注'] = 'ERROR器件名不完整'
                item = get_item(item)
                return item
            #item[u'备注'] = 'ERROR'
            #return item
        except Exception:
            try:
                no_result = soup.find('div', id='noResults').find('p').text
                if len(no_result) > 10:  # 错误类型
                    print("错误类型Error无该器件:", url)
                    item[u'备注'] = 'ERROR无该器件'
                    item = get_item(item)
                    return item
            except Exception:
                    print("正常型:", url)
                    return parse_detail(url, item, headers)
    except Exception:
        print("解析:", url, "失败")
        item = {}
        item = get_item(item)
        item['Manufacturer Part Number'] = keyword		
        item[u'备注'] = '解析失败'
        item = get_item(item)
        return item


def parse_unit(unit):
    if len(re.findall('hms', unit)) > 0:
        num = re.sub('\D+', "", unit)
        temp = re.findall('[A-Za-z]+hms', unit)
        if len(temp) > 0:
            if temp[0][0] == 'O':
                unit = str(num) + 'R'
            else:
                unit = str(num)+temp[0][0].upper()
        return unit
    return unit.replace('µ', 'u')


def parse_detail(url, item, headers):
    try:
        item[u'手册链接'] = url
        content = s.get(url, headers=headers).content
        soup = BeautifulSoup(content, 'lxml')
        #product_details = soup.find('table', id='product-details').find_all('tr')
        product_overview = soup.find('table', id='product-overview').find_all('tr')
        #print("this is  ok")
        try:
            product_dollars = soup.find('table', id='product-dollars').find_all('tr')
            item['Unit Price'] = product_dollars[1].find_all('td')[1].text.strip()
        except Exception:
            item['Unit Price'] = '-'
        item['Description'] = product_overview[4].find_all('td')[0].text.strip()
        item['Manufacturer'] = product_overview[3].find_all('td')[0].text.strip()
        #print("this is  ok",item['Description']) #this is debug 

        item['Schematic Part'] = ''
        item['PCB Footprint'] = ''
        #trs = soup.find('table', id='prod-att-table').find_all('tr')[2:]
        trs = soup.find('table', id='product-attribute-table').find_all('tr')[2:]   #新命名的数据名
        item['Part Type'] = trs[0].find_all('td')[0].text.strip()
        #print("this is  ok2",item['Part Type'])
        count = 0
        for tr in trs[1:]:
            categories = tr.find('th').text.strip()
            value = tr.find_all('td')[0].text.strip()
            if categories == 'Capacitance':
                item['Value'] = parse_unit(value)
            if categories == 'Resistance':
                item['Value'] = parse_unit(value)
            if categories == 'Manufacturer':
                item['Manufacturer'] = value
            if 'Operating Temperature' in categories:
                item['Operating Temperature'] = value
            if categories == 'Package / Case':
                item['Package / Case'] = value
            if categories == 'Mounting Type':
                item['Mounting Type'] = value
            if categories == 'Supplier Device Package':
                item['Supplier Device Package'] = value
            if categories == 'Series':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Tolerance':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Type':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Applications':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Contact Shape':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Contact Finish Thickness - Post':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Contact Finish - Post':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Current Rating':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Voltage Rating':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Voltage - Rated':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Features':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Height - Seated (Max)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Size / Dimension':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Inductance Frequency - Test':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Q @ Freq':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'DC Resistance (DCR)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Shielding':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Current - Saturation':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Material - Core':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Power (Watts)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Temperature Coefficient':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Composition':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Failure Rate':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Technology':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Drain to Source Voltage (Vdss)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Current - Continuous Drain (Id) @ 25°C':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Drive Voltage (Max Rds On, Min Rds On)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Rds On (Max) @ Id, Vgs':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Gate Charge (Qg) (Max) @ Vgs':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Vgs(th) (Max) @ Id':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Input Capacitance (Ciss) (Max) @ Vds':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'FET Feature':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Power Dissipation (Max)':
                count = count + 1
                item[u'重要参数' + str(count)] = value

            if categories == 'Synchronous Rectifier':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Base Part Number':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Frequency - Switching':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Current - Output':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Voltage - Output (Max)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Voltage - Output (Min/Fixed)':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Number of Outputs':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Output Type':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Topology':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Output Configuration':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Function':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'DC Resistance (DCR) (Max)':
                count = count + 1
                item[u'重要参数' + str(count)] = value

            if categories == 'Clamp Material - Plating':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Screw Material - Plating':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Torque - Screw':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Screw Thread':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Color':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Wire Termination':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Wire Gauge':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Mating Orientation':
                count = count + 1
                item[u'重要参数' + str(count)] = value
            if categories == 'Pitch':
                count = count + 1
                item[u'重要参数' + str(count)] = value
        if item['Value'] == ' ':
            item['Value'] = item['Manufacturer Part Number']
        if item['Mounting Type'] == ' ':
            item['Mounting Type'] = '-'
        if item['Supplier Device Package'] == ' ':
            item['Supplier Device Package'] = '-'
        if item['Operating Temperature'] == ' ':
            item['Operating Temperature'] = '-'
        if item['Manufacturer'] == ' ':
            item['Manufacturer'] = '-'
        if item['Package / Case'] == ' ':
            item['Package / Case'] = '-'

        for i in range(1, 11):
            if item['重要参数' + str(i)] == ' ':
                item['重要参数' + str(i)] = '-'
        return item
    except Exception:
        print("解析详情页失败!", url)
        print("需手动添加:", url)
        item[u'备注'] = '需手动添加'
        item = get_item(item)
        return item


if __name__ == '__main__':
    pre_url = 'https://www.digikey.com/products/en?keywords='
    file_name, part_numbers = get_data_from_xlsx()
    local_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    items = []
    columns = ['Part Type', 'Schematic Part', 'PCB Footprint', 'Manufacturer Part Number', 'Value',
               'Manufacturer', 'Description', 'Operating Temperature', 'Package / Case', 'Mounting Type',
               'Supplier Device Package', '重要参数1', '重要参数2', '重要参数3', '重要参数4', '重要参数5', '重要参数6',
               '重要参数7', '重要参数8', '重要参数9', '重要参数10', '手册链接', '是否检查', '备注', '是否缺货', 'Unit Price']
    print("==========================================================================")
    print("=====================Virtual test begins==================================")
    print("============= ignore the following warnings ==============================")
    test = "TPS2042BDR"
    parse(pre_url+test, test)
    print("If the following information likes above,please contact the administrator.")
    print("=====================Virtual test ends====================================")
    print("==========================================================================")
    print()
    print()
    print()
    print("=====================Real test begins=====================================")
    for part_number in part_numbers:
        part_number = str(part_number)
        url = pre_url+part_number
        item = parse(url=url, keyword=part_number)
        if item is not None:
            items.append(item)
    print("=====================Real test ends=======================================")
    temp = pd.DataFrame(items, columns=columns)
    temp.index.name = u"序号"
    file_name = file_name + "_Digikey_" + local_time + '.xlsx'
    temp.to_excel(file_name)

