import pathlib
import re
from urllib.parse import urljoin

import folium
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
from folium import plugins
from folium.features import DivIcon

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
}


def fetch_soup(url, parser="html.parser"):

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, parser)

    return soup


def fetch_file(url, dir="."):

    p = pathlib.Path(dir, pathlib.PurePath(url).name)
    p.parent.mkdir(parents=True, exist_ok=True)

    if not p.exists():

        r = requests.get(url)
        r.raise_for_status()

        with p.open(mode="wb") as fw:
            fw.write(r.content)

    return p


# スクレイピング
url = "https://www.city.imabari.ehime.jp/hoiku/"

soup = fetch_soup(url)

tag = soup.find("a", text=re.compile("受け入れ可能状況"), href=re.compile(".pdf$"))
link = urljoin(url, tag.get("href"))

# ダウンロード
p = fetch_file(link)

# PDF変換
with pdfplumber.open(p) as pdf:

    page = pdf.pages[0]
    table = page.extract_table()
    df = pd.DataFrame(table[1:], columns=table[0])

# データクレンジング
df.set_axis(
    ["分類", "施設名", "入所年齢", "０歳", "１歳", "２歳", "３歳", "４歳", "５歳"], axis=1, inplace=True
)

df["分類"] = df["分類"].str.replace("\s", "", regex=True).fillna(method="ffill")

df.loc[:, "０歳":"５歳"] = df.loc[:, "０歳":"５歳"].replace({"": "－"})

se = (
    df.loc[:, "０歳":"５歳"]
    .copy()
    .replace({"×": 0, "△": 1, "○": 3, "－": 0})
    .astype(int)
    .sum(axis=1)
)

df["color"] = pd.cut(
    se, [0, 1, 5, 10, 100], right=False, labels=["black", "red", "orange", "green"]
)

address = pd.read_csv(
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQNb3geohr8IyP2JFLjeE1sxfmCjkI_Zw5yxMehcq1aWtZMESVl_BXR7lz2O-64aFty4htZb8vumEEC/pub?gid=0&single=true&output=csv"
)

df_map = pd.merge(df, address, on="施設名")

p_csv = pathlib.Path("map", "data.csv")
df_map.to_csv(str(p_csv))

# 地図
map = folium.Map(
    location=[34.0662403, 132.9976865],
    zoom_start=14,
    tiles=None,
)

folium.raster_layers.TileLayer(
    tiles="https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
    name="国土地理院",
    attr='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>',
).add_to(map)

# 現在値
folium.plugins.LocateControl(position="bottomright").add_to(map)

# 距離測定
folium.plugins.MeasureControl().add_to(map)

fg1 = folium.FeatureGroup(name="募集中").add_to(map)
fg2 = folium.FeatureGroup(name="空きなし").add_to(map)

for i, r in df_map.iterrows():

    n = len(r["施設名"])

    if r["color"] != "black":

        fg1.add_child(
            folium.Marker(
                location=[r["緯度"], r["経度"]],
                popup=folium.Popup(
                    f'<table border="1" style="border-collapse: collapse"><tr><th>施設名</th><td>{r["施設名"]}</td></tr><tr><th>所在地</th><td>{r["所在地"]}</td></tr><tr><th>電話番号</th><td>{r["電話番号"]}</td></tr><tr><th>入所年齢</th><td>{r["入所年齢"]}</td></tr><tr><th>０歳</th><td>{r["０歳"]}</td></tr><tr><th>１歳</th><td>{r["１歳"]}</td></tr><tr><th>２歳</th><td>{r["２歳"]}</td></tr><tr><th>３歳</th><td>{r["３歳"]}</td></tr><tr><th>４歳</th><td>{r["４歳"]}</td></tr><tr><th>５歳</th><td>{r["５歳"]}</td></tr></table>',
                    max_width=300,
                ),
                icon=folium.Icon(color=r["color"]),
            ),
        )

        fg1.add_child(
            folium.Marker(
                location=[r["緯度"], r["経度"]],
                icon=DivIcon(
                    icon_size=(14 * n, 30),
                    icon_anchor=(7 * n, -5),
                    html=f'<div style="text-align:center; font-weight: bold; font-size: 10pt; background-color:rgba(255,255,255,0.8)">{r["施設名"]}</div>',
                ),
            )
        )

    else:

        fg2.add_child(
            folium.Marker(
                location=[r["緯度"], r["経度"]],
                popup=folium.Popup(
                    f'<table border="1" style="border-collapse: collapse"><tr><th>施設名</th><td>{r["施設名"]}</td></tr><tr><th>所在地</th><td>{r["所在地"]}</td></tr><tr><th>電話番号</th><td>{r["電話番号"]}</td></tr><tr><th>入所年齢</th><td>{r["入所年齢"]}</td></tr><tr><th>０歳</th><td>{r["０歳"]}</td></tr><tr><th>１歳</th><td>{r["１歳"]}</td></tr><tr><th>２歳</th><td>{r["２歳"]}</td></tr><tr><th>３歳</th><td>{r["３歳"]}</td></tr><tr><th>４歳</th><td>{r["４歳"]}</td></tr><tr><th>５歳</th><td>{r["５歳"]}</td></tr></table>',
                    max_width=300,
                ),
                icon=folium.Icon(color=r["color"]),
            )
        )

        fg2.add_child(
            folium.Marker(
                location=[r["緯度"], r["経度"]],
                icon=DivIcon(
                    icon_size=(14 * n, 30),
                    icon_anchor=(7 * n, -5),
                    html=f'<div style="text-align:center; font-weight: bold; font-size: 10pt; background-color:rgba(255,255,255,0.8)">{r["施設名"]}</div>',
                ),
            )
        )

folium.LayerControl().add_to(map)

p_map = pathlib.Path("map", "index.html")
map.save(str(p_map))
