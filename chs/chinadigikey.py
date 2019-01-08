# -*- coding: utf-8 -*-
# @Time     :  2018/12/27
# @Author   :  kunming Zhang
# @Function :  爬中文digikey的价格信息
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
    for i in range(1, 11):
        item['重要参数' + str(i)] = ' '
    return item

def parse(url, keyword):
    ua = UserAgent()
    pre_url = 'https://www.digikey.com.cn'

    headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
               'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
               'cache-control': 'max-age=0',
               'upgrade-insecure-requests': '1',
               'user-agent': ua.get_user_agent()}  # 得到随机User-Agent头
    try:
        body = s.get(url, headers=headers).text
        soup = BeautifulSoup(body, 'lxml')
        item = {}
        item = get_item(item)
        item['Manufacturer Part Number'] = keyword
        short_supply_flag = False
        current_keyword = ""
        minimum_quantity = 0
        RMB_price_USD = None
        # 两个个临时变量，保存缺货时的状态
        temp_minimum_quantity = minimum_quantity
        temp_RMB_price_USD = RMB_price_USD
        temp_fit_flag = False
        try:
            trs = soup.find('table', id='productTable').find_all('tr', attrs={'class': {'tblevenrow', 'tbloddrow'}})
            for tr in trs:
                tds = tr.find_all('td')
                current_keyword = tds[4].find('a').text
                new_url = pre_url + tds[4].find('a').get('href')
                try:
                    quantity_available = int(re.sub('\D+', "", tds[7].text.strip()))
                except Exception:
                    quantity_available = 0
                if quantity_available != 0 and current_keyword == keyword:
                    short_supply_flag = True
                RMB_price_RMB = tds[8].text.strip()
                try:
                    minimum_quantity = int(re.sub('\D+', "", tds[6].text.strip()))
                except Exception:
                    minimum_quantity = 0
                if current_keyword == keyword:
                    temp_fit_flag = True
                if current_keyword == keyword and quantity_available != 0 and minimum_quantity == 1 and has_numbers(RMB_price_RMB):  # 名称正确 有货 发货数量为1 有价格  则为正常
                    print("正常型", url)
                    item['器件状态'] = '正常'
                    item['是否缺货'] = '否'
                    item['RMB Price'] = RMB_price_RMB
                    item['手册链接'] = new_url
                    item['Part Type'] = parse_detail1(new_url, headers)
                    while item['Part Type'] == '需手动添加':
                        item['Part Type'] = parse_detail1(new_url, headers)
                    return item
                if current_keyword == keyword and quantity_available != 0 and minimum_quantity == 1:
                    print("无价格", url)  # test1 待修改
                    item['器件状态'] = '无价格'
                    item['是否缺货'] = '否'
                    item['RMB Price'] = RMB_price_RMB
                    item['手册链接'] = new_url
                    item['Part Type'] = parse_detail1(new_url, headers)
                    while item['Part Type'] == '需手动添加':
                        item['Part Type'] = parse_detail1(new_url, headers)
                    return item
                if current_keyword == keyword and quantity_available == 0 and minimum_quantity == 1:  # 名称正确 有货 发货数量为1 无价格   warning :缺货
                    print("缺货", url)  # test1 待修改
                    item['器件状态'] = '缺货'
                    item['是否缺货'] = '是'
                    item['RMB Price'] = RMB_price_RMB
                    item['手册链接'] = new_url
                    item['Part Type'] = parse_detail1(new_url, headers)
                    while item['Part Type'] == '需手动添加':
                        item['Part Type'] = parse_detail1(new_url, headers)
                    return item
            # 名称不对应
            if temp_fit_flag == False:  # 名称不正确
                print("错误类型Error器件名不完整:", url)
                item[u'器件状态'] = 'ERROR器件名不完整'
                return item
        except Exception:
            try:
                no_result = soup.find('div', id='noResults').find('p').text
                if len(no_result) > 10:  # 错误类型
                    print("错误类型Error无该器件:", url)
                    item[u'器件状态'] = 'ERROR无该器件'
                    return item
            except Exception:
                item['手册链接'] = url
                return parse_detail2(url, item, headers)
    except Exception:
        print("解析:", url, "失败")
        item = {}
        item = get_item(item)
        item['Manufacturer Part Number'] = keyword
        item[u'器件状态'] = '解析失败'
        item = get_item(item)
        return item

def parse_detail1(url, headers):
    try:
        content = s.get(url, headers=headers).text
        soup = BeautifulSoup(content, 'lxml')
        trs1 = soup.find('table', id='GeneralInformationTable').find_all('tr')[6:]
        res = trs1[0].find_all('td')[0].text.strip()
        return res
    except Exception:
        return '需手动添加'

def parse_detail2(url, item, headers):
    try:
        content = s.get(url, headers=headers).text
        soup = BeautifulSoup(content, 'lxml')
        trs1 = soup.find('table', id='GeneralInformationTable').find_all('tr')[6:]
        item['Part Type'] = trs1[0].find_all('td')[0].text.strip()
        temp_rmb_price = None
        temp_minimum_quantity = 0
        try:
            pricing = soup.find('table', id='pricing').find_all('tr')
            temp_minimum_quantity = pricing[1].find_all('td')[0].text.strip()  #
            temp_rmb_price = pricing[1].find_all('td')[2].text.strip()  # 订购价格
        except Exception:
            print(item['Manufacturer Part Number'] + " 无价格信息 " + url)
            item['器件状态'] = '缺货'
            item['是否缺货'] = '是'
            item['RMB Price'] = '-'
            return item
        # 正常型
        if temp_minimum_quantity == '1' and has_numbers(temp_rmb_price):
            print("正常型", url)
            item['器件状态'] = '正常'
            item['是否缺货'] = '否'
            item['RMB Price'] = temp_rmb_price
            return item
        # 无法单个发货
        if temp_minimum_quantity != '1' and has_numbers(temp_rmb_price):
            print("无法少量购买", url)
            item['器件状态'] = '无法少量购买'
            item['是否缺货'] = '否'
            item['RMB Price'] = temp_rmb_price + ' / ' + temp_minimum_quantity
            return item
        print("缺货", url)
        item['器件状态'] = '缺货'
        item['是否缺货'] = '是'
        item['RMB Price'] = '-'
        return item
    except Exception:
        print("解析详情页失败!", url)
        print("需手动添加:", url)
        item['器件状态'] = '需手动添加'
        return item

if __name__ == '__main__':
    pre_url = 'https://www.digikey.com.cn/products/zh?WT.z_header=search_go&keywords='
    file_name, part_numbers = get_data_from_xlsx()
    local_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    items = []
    columns = ['Part Type', 'Manufacturer Part Number', '手册链接', '器件状态', '是否缺货', 'RMB Price']
    for part_number in part_numbers:
        part_number = str(part_number)
        url = pre_url + part_number
        item = parse(url, part_number)
        if item is not None:
            items.append(item)
    temp = pd.DataFrame(items, columns=columns)
    temp.index.name = u"序号"
    file_name = file_name + "_Digikey.cn_" + local_time + '.xlsx'
    temp.to_excel(file_name)
