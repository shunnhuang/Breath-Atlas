import requests
import folium
import networkx as nx
from geopy.distance import geodesic

# ✅ 1. 获取伦敦地铁站点信息
tfl_stations_url = "https://api.tfl.gov.uk/StopPoint/Mode/tube"
response = requests.get(tfl_stations_url)
stations_data = response.json()

# 提取站点信息（站点 ID、名称、经纬度）
stations = {}
for station in stations_data['stopPoints']:
    station_id = station["id"]
    name = station["commonName"]
    lat = station["lat"]
    lon = station["lon"]
    stations[station_id] = {"name": name, "lat": lat, "lon": lon}

# ✅ 2. 获取空气质量数据（AQICN API）
API_KEY = "demo"  # 使用 AQICN Demo API
aqi_url = "http://api.waqi.info/search/?token={}&keyword=london".format(API_KEY)
aqi_response = requests.get(aqi_url)
aqi_data = aqi_response.json()

# 解析空气质量站点信息
aqi_stations = {}
if "data" in aqi_data:
    for site in aqi_data["data"]:
        if "station" in site and isinstance(site["station"], dict):
            name = site["station"].get("name", "Unknown")
            lat, lon = site["station"]["geo"]
            aqi_value = int(site["aqi"]) if site["aqi"].isdigit() else None
            if aqi_value is not None:
                aqi_stations[(lat, lon)] = {"name": name, "aqi": aqi_value}

# ✅ 3. 计算每个地铁站点最近的 AQI 站点
def find_nearest_aqi(lat, lon):
    nearest_aqi = None
    nearest_distance = float('inf')

    for (aqi_lat, aqi_lon), aqi_data in aqi_stations.items():
        distance = geodesic((lat, lon), (aqi_lat, aqi_lon)).km
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_aqi = aqi_data["aqi"]
    
    return nearest_aqi if nearest_aqi is not None else 100  # 默认 AQI 为 100（中等污染）

# ✅ 4. 计算地铁站点的空气质量
for station_id, station_info in stations.items():
    station_info["aqi"] = find_nearest_aqi(station_info["lat"], station_info["lon"])

# ✅ 5. 获取伦敦地铁路线数据（站点之间的连接）
tube_routes_url = "https://api.tfl.gov.uk/Line/Mode/tube/Route"
routes_response = requests.get(tube_routes_url)
routes_data = routes_response.json()

# ✅ 6. 创建地铁网络图
G = nx.Graph()

# 添加站点到图中
for station_id, station_info in stations.items():
    G.add_node(station_id, **station_info)

# ✅ 7. 修正 `G.add_edge()`，确保所有站点正确连接
def find_matching_station(name):
    """ 根据名称找到站点 ID """
    for station_id, station_info in stations.items():
        if name.lower() in station_info["name"].lower():
            return station_id
    return None

for route in routes_data:
    if "lineId" in route and "routeSections" in route:
        for section in route["routeSections"]:
            origin_name = section.get("originationName")
            dest_name = section.get("destinationName")

            match_origin = find_matching_station(origin_name)
            match_dest = find_matching_station(dest_name)

            if match_origin and match_dest:
                origin_aqi = stations[match_origin]["aqi"]
                dest_aqi = stations[match_dest]["aqi"]
                avg_aqi = (origin_aqi + dest_aqi) / 2

                # 添加站点连接
                G.add_edge(match_origin, match_dest, weight=avg_aqi)

# ✅ 8. 计算最佳路径（避开污染）
def find_least_polluted_path(start_station, end_station):
    try:
        best_path = nx.shortest_path(G, source=start_station, target=end_station, weight="weight")
        return best_path
    except nx.NetworkXNoPath:
        return None

# ✅ 9. 终端输入站点名称
start_station = input("请输入起点站（如 'Victoria Underground Station'）：")
end_station = input("请输入终点站（如 'Liverpool Street Underground Station'）：")

start_station_id = find_matching_station(start_station)
end_station_id = find_matching_station(end_station)

if not start_station_id or not end_station_id:
    print("❌ 站点名称不匹配，请检查输入")
    exit()

best_path = find_least_polluted_path(start_station_id, end_station_id)

if best_path:
    print("\n🚆 最佳低污染路径：")
    for station in best_path:
        print(f"{stations[station]['name']} (AQI: {stations[station]['aqi']})")
else:
    print("\n❌ 无法找到低污染路径")

# ✅ 10. 绘制地图
m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)

# 标注地铁站
for station_id, station_info in stations.items():
    folium.Marker(
        location=[station_info["lat"], station_info["lon"]],
        icon=folium.DivIcon(html=f"""
            <div style="background-color: rgba(255, 255, 255, 0.8);
                        border-radius: 5px;
                        padding: 5px;
                        font-size: 12px;
                        font-weight: bold;
                        text-align: center;
                        color: black;">
                {station_info["aqi"]}
            </div>
        """),
        popup=f"{station_info['name']}<br>AQI: {station_info['aqi']}"
    ).add_to(m)

# ✅ 11. 绘制最佳路线
if best_path:
    path_coords = [(stations[station]["lat"], stations[station]["lon"]) for station in best_path]
    folium.PolyLine(path_coords, color="green", weight=5, opacity=0.7).add_to(m)

# ✅ 12. 保存 HTML 地图
output_file = "london_clean_air_route.html"
m.save(output_file)
print(f"\n🌍 低污染地铁路线地图已生成: {output_file} 🚆")
