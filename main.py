import pathlib
import re
from urllib.parse import urljoin

import camelot
import folium
import pandas as pd
import requests
from bs4 import BeautifulSoup

url = "https://www.city.imabari.ehime.jp/hoiku/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
}

# スクレイピング

r = requests.get(url, headers=headers)
r.raise_for_status()

soup = BeautifulSoup(r.content, "html.parser")

tag = soup.find("a", text=re.compile("今治市受け入れ可能状況一覧"), href=re.compile(".pdf$"))
link = urljoin(url, tag.get("href"))

# 前処理

# PDFを変換

tables = camelot.read_pdf(
    link, pages="all", split_text=True, strip_text=" \n", line_scale=40
)

# データ

df = pd.DataFrame(tables[0].data[1:], columns=tables[0].data[0]).rename(
    columns={"施設名": "分類", "": "施設名"}
)

# 分類を補完

df["分類"] = df["分類"].mask(df["分類"] == "").fillna(method="ffill")

# 空き状況を数値化

df1 = df.loc[:, "０歳":"５歳"].copy()

free = (
    df1.apply(lambda s: s.map({"×": 0, "△": 1, "○": 3}))
    .fillna(0)
    .astype(int)
    .sum(axis=1)
)

# 空き状況を色に変換

df["color"] = pd.cut(
    free, [0, 1, 5, 10, 100], right=False, labels=["black", "red", "orange", "green"]
)

# 保育園の位置情報を読み込み

address = pd.read_csv(
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQNb3geohr8IyP2JFLjeE1sxfmCjkI_Zw5yxMehcq1aWtZMESVl_BXR7lz2O-64aFty4htZb8vumEEC/pub?gid=0&single=true&output=csv"
)


# 空き状況と位置情報を結合

df_map = pd.merge(df, address, on="施設名")

# マップ化

map = folium.Map(location=[34.06604300, 132.99765800], zoom_start=10)

for i, r in df_map.iterrows():
    folium.Marker(
        location=[r["緯度"], r["経度"]],
        popup=folium.Popup(
            f'<table border="1" style="border-collapse: collapse"><tr><th>施設名</th><td>{r["施設名"]}</td></tr><tr><th>所在地</th><td>{r["所在地"]}</td></tr><tr><th>電話番号</th><td>{r["電話番号"]}</td></tr><tr><th>入所年齢</th><td>{r["入所年齢"]}</td></tr><tr><th>０歳</th><td>{r["０歳"]}</td></tr><tr><th>１歳</th><td>{r["１歳"]}</td></tr><tr><th>２歳</th><td>{r["２歳"]}</td></tr><tr><th>３歳</th><td>{r["３歳"]}</td></tr><tr><th>４歳</th><td>{r["４歳"]}</td></tr><tr><th>５歳</th><td>{r["５歳"]}</td></tr></table>',
            max_width=300,
        ),
        icon=folium.Icon(color=r["color"]),
    ).add_to(map)

# ファイルに保存

p_map = pathlib.Path("map", "index.html")
map.save(str(p_map))
