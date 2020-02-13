#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright By Eric in 2020

import datetime
import pandas as pd
from pymongo import MongoClient
from pyecharts import options as opts
from pyecharts.charts import Geo, Map, Line, Page
from pyecharts.globals import ChartType


class CleanData(object):
    def __init__(self):
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.client = MongoClient('localhost', port=27017)
        self.db = self.client.NCP

    def change_data(self):
        collection = self.db[self.now_date]
        data_all = pd.DataFrame(collection.find({}, {'_id': 0}))
        temp = data_all[['province', 'city', 'pos_lon',
                         'pos_lat', 'total_confirm']].copy()  # copy()一个副本
        total_china = temp['total_confirm'].sum()      # 统计库中确诊总数
        temp['name'] = temp['province'] + temp['city']      # 合并省、市两列
        temp['pos'] = temp.apply(
            lambda row: [
                row['pos_lon'],
                row['pos_lat']],
            axis=1)     # 用apply()方法合并经纬度两列
        temp_position = temp[['pos', 'name']]

        temp_china = temp[~temp['province'].isin(['湖北'])]       # 用反选去除湖北数据
        china_confirm = temp_china[['name', 'total_confirm']].values.tolist()   # 提取两列转换列表
        temp_hubei = temp[temp['province'].isin(['湖北'])]        # 选择湖北数据
        hubei_confirm = temp_hubei[['city', 'total_confirm']].values.tolist()   # 提取两列转换列表
        total_hubei = temp_hubei['total_confirm'].sum()        # 统计湖北确诊总数

        temp_position.set_index(['name'], inplace=True)     # 用省市名称重建索引
        data_position = pd.Series(
            temp_position.pos.values,
            index=temp_position.index)      # 转换为Series格式
        with open('position.json', 'w', encoding='utf-8') as f:
            f.write(data_position.to_json(orient='index', force_ascii=False))   # 用to_json方法输出文件
        data_confirm = [china_confirm, hubei_confirm, total_china, total_hubei]
        return data_confirm

    def change_days(self):
        collection = self.db.ChinaDayList
        data_all = pd.DataFrame(collection.find({}, {'_id': 0}))
        date = data_all['date'].tolist()
        confirm = data_all['confirm'].tolist()
        dead = data_all['dead'].tolist()
        heal = data_all['heal'].tolist()
        daylist = [date, confirm, dead, heal]
        return daylist


class DrawMap(object):
    def __init__(self):
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')

    def geo_china(self, data, total):
        china_map = (
            Geo(init_opts=opts.InitOpts(width='1000px', height='500px'))
            .add_schema(maptype="china", zoom=1.2)
            # 从json文件导入坐标值
            .add_coordinate_json('position.json')
            .add('', data, symbol_size=10, color='#4c221b')
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts
            (
                visualmap_opts=opts.VisualMapOpts(
                    type_='color', min_=0, max_=50),
                title_opts=opts.TitleOpts(title='全国疫情确诊病例分布图（散点）',
                                          subtitle='截止{}，全国{}个城市和地区(未含湖北)共确诊{}例'
                                          .format(self.now_date, len(data), total))
            )
        )
        return china_map

    def geo_china_piecewise(self, data, total):
        china_map = (
            Geo(init_opts=opts.InitOpts(width='1000px', height='500px'))
            .add_schema(maptype="china", zoom=1.2)
            .add_coordinate_json('position.json')
            .add('', data, symbol_size=10, color='#4c221b')
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts
            (
                visualmap_opts=opts.VisualMapOpts(
                    type_='color', min_=0, max_=200, is_piecewise=True),
                title_opts=opts.TitleOpts(title='全国疫情确诊病例分布图（分段）',
                                          subtitle='截止{}，全国{}个城市和地区(未含湖北)共确诊{}例'
                                          .format(self.now_date, len(data), total))
            )
        )
        return china_map

    def heat_china(self, data, total):
        china_map = (
            Geo(init_opts=opts.InitOpts(width='1000px', height='500px'))
            .add_schema(maptype="china", zoom=1.2)
            .add_coordinate_json('position.json')
            .add('', data, symbol_size=10, color='#4c221b', type_=ChartType.HEATMAP)
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts
            (
                visualmap_opts=opts.VisualMapOpts(
                    type_='color', min_=0, max_=200),
                title_opts=opts.TitleOpts(title='全国疫情确诊病例热力图',
                                          subtitle='截止{}，全国{}个城市和地区(未含湖北)共确诊{}例'
                                          .format(self.now_date, len(data), total))
            )
        )
        return china_map

    def map_hubei(self, data, total):
        data_clean = CleanHubeiData.cleans(data)
        hubei_map = (
            Map(init_opts=opts.InitOpts(width='1000px', height='500px'))
            .add('湖北', data_clean, maptype="湖北", is_map_symbol_show=True, is_roam=True, zoom=1)
            .set_global_opts
            (
                visualmap_opts=opts.VisualMapOpts(min_=0, max_=2000),
                title_opts=opts.TitleOpts(title='湖北疫情确诊病例分布图',
                                          subtitle='截止{}，湖北{}个城市和地区共确诊{}例'
                                          .format(self.now_date, len(data), total)),
                legend_opts=opts.LegendOpts(is_show=True),  # 图例配置项
            )
            .set_series_opts  # 设置系列配置项
            (
                label_opts=opts.LabelOpts(is_show=True),
                itemstyle_opts=opts.ItemStyleOpts(
                    color='rgba(255, 255, 255, 0)')
            )
        )
        return hubei_map

    def line_days(self, data):
        days_line = (
            Line(init_opts=opts.InitOpts(width='1000px', height='500px'))
            .add_xaxis(data[0])
            .add_yaxis('确诊', data[1], is_smooth=True, symbol='circle', symbol_size=6)
            .add_yaxis('死亡', data[2], is_smooth=True, symbol='circle', symbol_size=6)
            .add_yaxis('康复', data[3], is_smooth=True, symbol='circle', symbol_size=6)
            .set_global_opts
            (
                title_opts=opts.TitleOpts(title='全国确诊、康复、死亡人数趋势图',
                                          subtitle='截止{}，共有{}天的数据'
                                          .format(self.now_date, len(data[0]))),
            )
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False, font_size=9))
        )
        return days_line


class CleanHubeiData(object):
    @classmethod
    def cleans(cls, data):
        data_cleaned = []
        for n in data:
            if n[0] == '恩施州':
                city = '恩施土家族苗族自治州'
            elif n[0] == '神农架':
                city = '神农架林区'
            else:
                city = n[0] + '市'
            data_cleaned.append([city, n[1]])
        return data_cleaned


def main():
    page = Page()
    ncp_map = DrawMap()
    cleandata = CleanData()
    confirm = cleandata.change_data()
    daylist = cleandata.change_days()

    page.add(ncp_map.line_days(daylist))
    page.add(ncp_map.geo_china(confirm[0], confirm[2]))
    page.add(ncp_map.geo_china_piecewise(confirm[0], confirm[2]))
    page.add(ncp_map.heat_china(confirm[0], confirm[2]))
    page.add(ncp_map.map_hubei(confirm[1], confirm[3]))

    page.render('NCP.html')
    print('数据地图生成完毕，请打开浏览器查看，多谢......')


if __name__ == '__main__':
    main()
