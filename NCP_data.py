#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright By Eric in 2020

import json
import datetime
import requests
from tqdm.std import trange
from pymongo import MongoClient


class Ncp(object):
    def __init__(self):
        self.client = MongoClient('localhost', port=27017)
        self.db = self.client.NCP
        self.collection_list = self.db.list_collection_names(
            session=None)  # 获取数据库中集合名称列表
        self.key = '47f1c118fa39425ab3f55e4339399e54'
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.url = 'https://view.inews.qq.com/g2/getOnsInfo?name=disease_h5'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/79.0.3945.130 Safari/537.36'}

    def location(self, province, city):
        url_loc = 'https://restapi.amap.com/v3/geocode/geo?address=' + \
                  province + city + '&key=' + self.key
        req = requests.get(url_loc)
        data = json.loads(req.text)
        if data['count'] == '0':  # 去除不能生成地理位置坐标的数据
            return
        pos = data['geocodes'][0]['location'].split(',')
        if float(pos[0]) == 0 or float(pos[1]) == 0:  # 去除坐标值为0的数据
            return
        pos_lon_lat = [float(pos[0]), float(pos[1])]
        return pos_lon_lat

    def get_data_all(self):
        req = requests.get(url=self.url, headers=self.headers)
        data_all = json.loads(req.text)
        return data_all

    def save_daylist(self):
        collection = self.db.ChinaDayList
        day_list = json.loads(self.get_data_all()['data'])['chinaDayList']
        for item in day_list:
            day_item = {
                'confirm': item['confirm'],
                'suspect': item['suspect'],
                'dead': item['dead'],
                'heal': item['heal'],
                'deadrate': item['deadRate'],
                'healrate': item['healRate'],
                'date': item['date']
            }
            collection.insert_one(day_item)

    def save_data(self):
        if self.now_date in self.collection_list:        # 判断库中是否已存在当天数据
            collection = self.db[self.now_date]
            print(
                '数据库中已有今天的数据{}条，请不要重复收集......'.format(
                    collection.count_documents(
                        {})))
            return collection
        else:
            collection = self.db[self.now_date]

        data_china = json.loads(self.get_data_all()['data'])[
            'areaTree'][0]     # 定位到中国数据
        country = data_china['name']      # 国家名称
        for prov_n in trange(len(data_china['children'])):       # 调用tqdm库显示进度
            data_province = data_china['children'][prov_n]      # 定位到省级数据
            province = data_province['name']        # 省份名称
            for city_n in range(len(data_province['children'])):
                data_city = data_province['children'][city_n]       # 定位到城市数据
                city = data_city['name']        # 城市名称
                isupdated = data_city['today']['isUpdated']     # 是否更新
                today_confirm = data_city['today']['confirm']       # 当天确诊数
                total_confirm = data_city['total']['confirm']       # 总确诊数
                total_heal = data_city['total']['heal']     # 总恢复数
                total_dead = data_city['total']['dead']     # 总死亡数
                pos_lon_lat = self.location(province, city)
                if pos_lon_lat is None:     # 如果返回的坐标为空值，则设置这条数据为省会
                    pos_lon_lat = self.location(province, province)
                item = {
                    'country': country,
                    'province': province,
                    'city': city,
                    'isupdated': isupdated,
                    'today_confirm': today_confirm,
                    'total_confirm': total_confirm,
                    'total_heal': total_heal,
                    'total_dead': total_dead,
                    'pos_lon': pos_lon_lat[0],
                    'pos_lat': pos_lon_lat[1]
                }
                collection.insert_one(item)
        print(
            '\n今天的数据已收集完毕，共采集了{}个城市和地区的数据......'.format(
                collection.count_documents(
                    {})))
        return


def main():
    ncp = Ncp()
    ncp.save_data()
    ncp.save_daylist()


if __name__ == '__main__':
    main()
