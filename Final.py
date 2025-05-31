import numpy as np
import pandas as pd
import requests
import folium
import networkx as nx
import dash
from dash import dcc, html
from dash.dependencies import Input as DashInput, Output, State
import plotly.graph_objects as go
from geopy.distance import geodesic
import dash_leaflet as dl
import dash_leaflet.express as dlx
import matplotlib.pyplot as plt
import math

# 获取伦敦地铁数据
TFL_STATIONS_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"
TFL_ROUTES_URL = "https://api.tfl.gov.uk/Line/Mode/tube/Route"

def get_london_tube_data():
    stations_response = requests.get(TFL_STATIONS_URL)
    routes_response = requests.get(TFL_ROUTES_URL)
    stations_data = stations_response.json()
    routes_data = routes_response.json()
    
    stations = {}
    for station in stations_data['stopPoints']:
        station_id = station["id"]
        name = station["commonName"]
        lat = station["lat"]
        lon = station["lon"]
        stations[station_id] = {"name": name, "lat": lat, "lon": lon}
    
    routes = []
    for route in routes_data:
        if "routeSections" in route:
            for section in route["routeSections"]:
                routes.append((section["originationName"], section["destinationName"]))
    
    print(f"Loaded {len(stations)} stations and {len(routes)} routes.")
    return stations, routes

stations, routes = get_london_tube_data()

# --- Dash 应用 ---
app = dash.Dash(__name__)
app.layout = html.Div([
    html.Div([
        html.Label("Select Time (Hour):", style={'color': 'white', 'fontSize': '18px', 'fontFamily': 'Arial'}),
        dcc.Slider(
            id='time-slider',
            min=0, max=23, step=1,
            marks={i: str(i) for i in range(24)},
            value=0,
            tooltip={"placement": "bottom", "always_visible": True}
        ),
        html.Label("Start Station:", style={'color': 'white', 'fontSize': '18px', 'fontFamily': 'Arial'}),
        dcc.Input(id='start-station', type='text', value='Victoria Underground Station', style={'width': '100%', 'padding': '10px', 'borderRadius': '10px'}),
        html.Label("End Station:", style={'color': 'white', 'fontSize': '18px', 'fontFamily': 'Arial'}),
        dcc.Input(id='end-station', type='text', value='Liverpool Street Underground Station', style={'width': '100%', 'padding': '10px', 'borderRadius': '10px'}),
        html.Button("Generate Route", id='generate-button', n_clicks=0, style={'backgroundColor': '#ff5733', 'color': 'white', 'padding': '15px', 'fontSize': '18px', 'border': 'none', 'borderRadius': '10px', 'marginTop': '10px'}),
    ], style={'width': '100%', 'padding': '20px', 'backgroundColor': '#1a1a1a', 'borderRadius': '10px', 'margin': '10px', 'textAlign': 'center'}),
    html.Div([
        html.Iframe(id='map', style={'height': '80vh', 'width': '100%', 'border': '2px solid #ff5733', 'borderRadius': '10px', 'margin': '10px'})
    ], style={'width': '100%', 'textAlign': 'center'})
], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center', 'alignItems': 'center', 'backgroundColor': '#282828', 'height': '100vh'})

@app.callback(
    Output('map', 'srcDoc'),
    DashInput('generate-button', 'n_clicks'),
    State('time-slider', 'value'),
    State('start-station', 'value'),
    State('end-station', 'value')
)
def update_map(n_clicks, selected_time, start_station, end_station):
    if n_clicks == 0:
        return None  # Wait for user to click the button
    
    # 重新获取数据，避免 API 失效
    stations, routes = get_london_tube_data()
    
    # 创建 Folium 地图
    m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)
    
    # 标记所有地铁站
    for station_id, station_info in stations.items():
        folium.Marker(location=[station_info["lat"], station_info["lon"]], 
                      popup=station_info["name"], 
                      icon=folium.Icon(color='gray')).add_to(m)
    
    # 绘制地铁线路
    for start, end in routes:
        start_coords = next((s for s in stations.values() if s['name'] == start), None)
        end_coords = next((s for s in stations.values() if s['name'] == end), None)
        if start_coords and end_coords:
            folium.PolyLine([(start_coords['lat'], start_coords['lon']), 
                             (end_coords['lat'], end_coords['lon'])], 
                             color='blue', weight=3).add_to(m)
    
    return m._repr_html_()

if __name__ == '__main__':
    app.run(debug=True)