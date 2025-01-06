import streamlit as st
import requests
import json
import pydeck as pdk
import pandas as pd
import folium
from streamlit_folium import folium_static


# Azure Maps Configuration
azure_maps_client_id = 'e6b6ab59-eb5d-4d25-aa57-581135b927f0'
token_service_url = 'https://samples.azuremaps.com/api/GetAzureMapsToken'
weather_request_url = 'https://atlas.microsoft.com/weather/currentConditions/json?api-version=1.0&query={query}&subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl'

# Waypoints
# waypoints = [
#     [-122.336502, 47.606544],
#     [-122.204821, 47.759892],
#     [-122.120415, 47.670682],
#     [-122.213369, 47.480133],
#     [-122.193689, 47.615556],
#     [-122.206054, 47.676508],
#     [-122.360861, 47.495472]
# ]

def get_token():
    response = requests.get(token_service_url)
    if response.status_code == 200:
        return response.text()
    else:
        st.error("Failed to retrieve Azure Maps token.")
        return None

def fetch_weather_data(query):
    weather_url = weather_request_url.replace('{query}', query)
    response = requests.get(weather_url)
    if response.status_code == 200:
        display_weather_data(response.json()['results'][0])
        return response.json()
    else:
        st.error("Failed to fetch weather data")
        return None

def display_weather_data(weather_data):
    st.subheader("Weather Information")
    
    # Create a dictionary with the relevant weather data
    weather_dict = {
        "Temperature (°C)": [weather_data['realFeelTemperature']['value']],
        "Weather": [weather_data['phrase'].capitalize()],
        "Humidity (%)": [weather_data['relativeHumidity']],
        "Wind Speed (m/s)": [weather_data['wind']['speed']['value'] / 3.6]  # Convert km/h to m/s
    }
    
    # Convert the dictionary to a DataFrame
    weather_df = pd.DataFrame(weather_dict)
    
    # Display the DataFrame as a table
    st.table(weather_df)


def calculate_route(waypoints,optimized=False):
    
    
    if all(-90 <= wp[0] <= 90 and -180 <= wp[1] <= 180 for wp in waypoints):
        # Format: (latitude, longitude)
        waypoint_query = ":".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
    else:
        # Format: (longitude, latitude)
        waypoint_query = ":".join([f"{wp[1]},{wp[0]}" for wp in waypoints])
    print(waypoint_query)
    rest_routing_request_url = f'https://atlas.microsoft.com/route/directions/json?subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&api-version=1.0&query={waypoint_query}&routeRepresentation=polyline&travelMode=car&view=Auto'
    
    if optimized:
        rest_routing_request_url += '&computeBestOrder=true'
    
    response = requests.get(rest_routing_request_url)
    print(response)
    if response.status_code == 200:
        result = response.json()
        route = result['routes'][0]
        
        add_route_to_map(route, optimized, result , waypoints)
    else:
        st.error("Failed to calculate route.")
    
def add_route_to_map(route, optimized, result , waypoints):
    route_coordinates = []
    for leg in route['legs']:
        for point in leg['points']:
            route_coordinates.append([point['latitude'], point['longitude']])

    # Create a Folium map centered at the first point of the route
    map_center = route_coordinates[0]
    folium_map = folium.Map(location=map_center, zoom_start=10)

    
    # Add markers for each waypoint
    for idx, coord in enumerate(waypoints):
        if all(-90 <= wp[0] <= 90 and -180 <= wp[1] <= 180 for wp in waypoints):
            coord = coord
        else:
            coord = coord[::-1]
        folium.Marker(
            location=coord,  # Reverse to [latitude, longitude]
            popup=f"Waypoint {idx + 1}",
            icon=folium.Icon(color="red")
        ).add_to(folium_map)

    # Add the route to the map
    folium.PolyLine(route_coordinates, color="blue", weight=5).add_to(folium_map)

    # Display the map using st_folium
    folium_static(folium_map, width=800, height=600)

    fetch_weather_data(f"{route_coordinates[0][0]},{route_coordinates[0][1]}")
    # Display output details
    output = f"Distance: {round(route['summary']['lengthInMeters'] / 1000, 2)} km\n"
    travel = f"Travel Time: {round(route['summary']['travelTimeInSeconds'] / 3600, 2)} hours\n"
    way = ''
    if optimized:
        pin_order = [0]
        for wp in result['optimizedWaypoints']:
            pin_order.append(wp['optimizedIndex'] + 1)
        pin_order.append(len(waypoints) - 1)
        way += f"Waypoint Order: {', '.join(map(str, pin_order))}"
    else:
        way += f"Waypoint Order: {', '.join(map(str, range(len(waypoints))))}"

    st.subheader(output)
    st.subheader(travel)
    st.subheader(way)

def waypoint():
    # Streamlit App Layout
    st.title("Route Waypoint Optimization - Delivery Route Planning")
    # st.write("This sample shows how to calculate routes with and without waypoint optimization using the Azure Maps REST Route API.")
    st.write("Enter the coordinates of the waypoints to calculate the optimized route. or else just press the button to see the default waypoints route.", key = 'waypoint')
    # Input for waypoints
    waypoints_input = st.text_area("Enter waypoints (comma-separated, e.g., -122.336502,47.606544,-122.204821,47.759892):" , key='waypoints_input')

    # Parse input waypoints
    if waypoints_input:
        try:
            waypoints_list = waypoints_input.split(',')
            waypoints = [[float(waypoints_list[i]), float(waypoints_list[i+1])] for i in range(0, len(waypoints_list), 2)]
        except ValueError:
            st.error("Invalid input format. Please enter valid coordinates.")
    else:
        # Default waypoints
        waypoints = [
            [-122.336502, 47.606544],
            [-122.204821, 47.759892],
            [-122.120415, 47.670682],
            [-122.213369, 47.480133],
            [-122.193689, 47.615556],
            [-122.206054, 47.676508],
            [-122.360861, 47.495472]
        ]


    if st.button("Calculate Waypoint Optimized Route"):
        calculate_route(waypoints , optimized=True)
    if st.button("Calculate Route"):
        calculate_route(waypoints=waypoints)
        
    
        


waypoint()