import streamlit as st
import requests
import json
from streamlit_folium import folium_static
import folium
import pandas as pd
from datetime import datetime

# st.sidebar.image("fedex-logo.svg")

# Azure Maps API URLs
geocode_request_url = 'https://atlas.microsoft.com/geocode?subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&api-version=2023-06-01&query={query}&view=Auto'
car_routing_request_url = 'https://atlas.microsoft.com/route/directions/json?subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&api-version=1.0&query={query}&routeRepresentation=polyline&travelMode=car&view=Auto'
truck_routing_request_url = 'https://atlas.microsoft.com/route/directions/json?subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&api-version=1.0&query={query}&routeRepresentation=polyline&vehicleLength={vehicleLength}&vehicleHeight={vehicleHeight}&vehicleWidth={vehicleWidth}&vehicleWeight={vehicleWeight}&vehicleLoadType={vehicleLoadType}'
weather_request_url = 'https://atlas.microsoft.com/weather/currentConditions/json?api-version=1.0&query={query}&subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl'

# Azure Maps client ID and token service URL
azure_maps_client_id = 'c901f16d-d6c6-45f4-98d3-0c89b0096dbf'
token_service_url = 'https://samples.azuremaps.com/api/GetAzureMapsToken'

def display_route_summary(summary):
    st.subheader("Route Summary")
    
    length_km = summary['lengthInMeters'] / 1000
    travel_time_hours = summary['travelTimeInSeconds'] / 3600
    traffic_delay_minutes = summary['trafficDelayInSeconds'] / 60
    traffic_length_km = summary['trafficLengthInMeters'] / 1000
    
    summary_dict = {
        "Length (km)": [round(length_km, 2)],
        "Travel Time (hours)": [round(travel_time_hours, 2)],
        "Traffic Delay (minutes)": [round(traffic_delay_minutes, 2)],
        "Traffic Length (km)": [round(traffic_length_km, 2)],
        "Departure Time": [datetime.fromisoformat(summary['departureTime']).strftime('%Y-%m-%d %H:%M:%S')],
        "Arrival Time": [datetime.fromisoformat(summary['arrivalTime']).strftime('%Y-%m-%d %H:%M:%S')]    
    }
    
    summary_df = pd.DataFrame(summary_dict)
    st.table(summary_df)

# Function to retrieve an Azure Maps access token
def get_token():
    response = requests.get(token_service_url)
    if response.status_code == 200:
        return response.text()
    else:
        st.error("Failed to retrieve Azure Maps token.")
        return None

# Function to geocode a query
def geocode_query(query):
    request_url = geocode_request_url.replace('{query}', query)
    response = requests.get(request_url)
    if response.status_code == 200:
        result = response.json()
        print(result)
        if result['features']:
            return result['features'][0]['geometry']['coordinates']
    return None

# Function to calculate directions
def calculate_directions(from_coord, to_coord, vehicle_options):
    print(from_coord, to_coord)
    from_coord_str = ','.join(map(str, from_coord[::-1]))
    to_coord_str = ','.join(map(str, to_coord[::-1]))
    query = f"{from_coord_str}:{to_coord_str}"

    print(query)
    # Car route
    car_request_url = car_routing_request_url.replace('{query}', query)
    car_response = requests.get(car_request_url)
    car_route = car_response.json()['routes'][0]['legs'][0]['points']

    display_route_summary(car_response.json()['routes'][0]['summary'])
    # Truck route
    truck_request_url = truck_routing_request_url.replace('{query}', query)
    for option, value in vehicle_options.items():
        truck_request_url = truck_request_url.replace(f'{{{option}}}', value)

    truck_response = requests.get(truck_request_url)
    truck_route = truck_response.json()['routes'][0]['legs'][0]['points']

    # st.write("Car Route:", car_route)
    print(car_route, truck_route)
    return car_route, truck_route

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

def get_location_from_coordinates(query):
    url = f'https://atlas.microsoft.com/search/address/reverse/json?api-version=1.0&subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&language=en-US&query={query}'
    response = requests.get(url)
    print(query)
    print(response.json())
    return response.json()['addresses'][0]['address']['freeformAddress']

def calculate_emissions(from_location, to_location, vehicle_options):
    url = 'https://api.climatiq.io/freight/v2/intermodal'
    headers = {
        'Authorization': 'Bearer H87YYQR7PN22KAJ8PZ9J8Y8HK8',
        'Content-Type': 'application/json'
    }
    data = {
        "route": [
            { "location": { "query": get_location_from_coordinates(from_location) } },
            {
                "transport_mode": "road",
                "leg_details": {
                    "rest_of_world": {
                        "vehicle_type": "van",
                        "vehicle_weight": "lte_3.5t",
                        "fuel_source": "petrol"
                    },
                    "india": {
                        "vehicle_type": "moving"
                    }
                }
            },
            { "location": { "query": get_location_from_coordinates(to_location) } }
        ],
        "cargo": {
            "weight": 10,
            "weight_unit": "kg"
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    emission_data = response.json()

    total_co2e = emission_data['co2e']
    vehicle_operation_co2e = emission_data['vehicle_operation_co2e']
    vehicle_energy_provision_co2e = emission_data['vehicle_energy_provision_co2e']
    distance_km = emission_data['distance_km']
    co2e_unit = emission_data['co2e_unit']
    
    st.write(f"### Emission Details")
    st.write(f"**Total CO2e:** {total_co2e} {co2e_unit}")
    st.write(f"**Vehicle Operation CO2e:** {vehicle_operation_co2e} {co2e_unit}")
    st.write(f"**Vehicle Energy Provision CO2e:** {vehicle_energy_provision_co2e} {co2e_unit}")
    st.write(f"**Distance:** {distance_km} km")

    for route in emission_data['route']:
        if route['type'] == 'leg':
            st.write(f"#### Leg Details")
            st.write(f"**Leg CO2e:** {route['co2e']} {route['co2e_unit']}")
            st.write(f"**Transport Mode:** {route['transport_mode']}")
            st.write(f"**Distance:** {route['distance_km']} km")
            st.write(f"**Vehicle Operation CO2e:** {route['vehicle_operation_co2e']} {route['co2e_unit']}")
            st.write(f"**Vehicle Energy Provision CO2e:** {route['vehicle_energy_provision_co2e']} {route['co2e_unit']}")

    
    return response.json()

def route():
    # Streamlit app
    st.title("Route Optimization")

    from_location = st.sidebar.text_input("From", "13.124557, 80.051936")
    to_location = st.sidebar.text_input("To", "13.075427, 80.199814")


    vehicle_options = {
        'vehicleLength': st.sidebar.text_input("Vehicle Length (meters)"),
        'vehicleHeight': st.sidebar.text_input("Vehicle Height (meters)"),
        'vehicleWidth': st.sidebar.text_input("Vehicle Width (meters)"),
        'vehicleWeight': st.sidebar.text_input("Vehicle Weight (kg)"),
        'vehicleLoadType': st.sidebar.selectbox("Vehicle Load Type", ["", "USHazmatClass1", "USHazmatClass2", "USHazmatClass3", "USHazmatClass4", "USHazmatClass5", "USHazmatClass6", "USHazmatClass7", "USHazmatClass8", "USHazmatClass9", "otherHazmatExplosive", "otherHazmatGeneral", "otherHazmatHarmfulToWater"])
    }

    if st.button("Calculate Directions"):
        from_coord = geocode_query(from_location)
        to_coord = geocode_query(to_location)
        
        emissions = calculate_emissions(from_location, to_location, vehicle_options)
        # st.write("Emissions Calculation Result:")
        # st.json(emissions)
        
        if from_coord and to_coord:
            car_route, truck_route = calculate_directions(from_coord, to_coord, vehicle_options)

            # Create map
            map_center = [(from_coord[1] + to_coord[1]) / 2, (from_coord[0] + to_coord[0]) / 2]
            folium_map = folium.Map(location=map_center, zoom_start=13)

            # Add car route
            print(from_coord)
            print(car_route[0])
            folium.Marker(
                location=from_coord[::-1],
                popup="From Location",
                icon=folium.Icon(icon="cloud", color="blue")
            ).add_to(folium_map)
            
            folium.Marker(
                location=to_coord[::-1],
                popup="To Location",
                icon=folium.Icon(icon="cloud", color="green")
            ).add_to(folium_map)
            folium.PolyLine([(point['latitude'], point['longitude']) for point in car_route], color="green", weight=2.5, opacity=1).add_to(folium_map)
            # Add truck route
            folium.PolyLine([(point['latitude'], point['longitude']) for point in truck_route], color="red", weight=2.5, opacity=1).add_to(folium_map)
            

            # Display map
            folium_static(folium_map)

            fetch_weather_data(from_location)
        else:
            st.error("Failed to geocode locations.")