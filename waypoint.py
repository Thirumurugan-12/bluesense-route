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

def get_location_from_coordinates(query,reverse=0):
    url = f'https://atlas.microsoft.com/search/address/reverse/json?api-version=1.0&subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&language=en-US&query={query}'
    response = requests.get(url)
    print('---------------------')
    print(url)
    if response.status_code == 200:
        print(response.json())
        if (reverse==1):
            return response.json()['addresses'][0]['address']['municipality']
        return response.json()['addresses'][0]['address']['freeformAddress']
    else:
        st.error("Failed to retrieve location data")
        return None

def calculate_emissions(locations, vehicle_options):
    url = 'https://api.climatiq.io/freight/v2/intermodal'
    headers = {
        'Authorization': 'Bearer H87YYQR7PN22KAJ8PZ9J8Y8HK8',
        'Content-Type': 'application/json'
    }
    
    route = []
    for location in locations:
        coords = get_location_from_coordinates(",".join(map(str, location)))
        if not coords:
            st.error(f"Invalid location data for {location}")
            return
        route.append({ "location": { "query": coords } })
    
    print(route)
    # Add transport mode details between waypoints
    for i in range(len(route) - 1):
        route.insert(2*i + 1, {
            "transport_mode": "road",
            "leg_details": {
                "rest_of_world": {
                    "vehicle_type": "van",
                    "vehicle_weight": "lte_3.5t",
                    "fuel_source": "petrol"
                },
                "north_america": {
                    "vehicle_type": "moving"
                }
            }
        })

    data = {
        "route": route[:7],
        "cargo": {
            "weight": float(vehicle_options['vehicleWeight']),
            "weight_unit": "kg"
        }
    }
    
    print(data)
    print(url)
    response = requests.post(url, headers=headers, data=json.dumps(data))
    emission_data = response.json()

    print(emission_data)
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

    # Define thresholds for dangerous emissions
    dangerous_threshold = 1000  # Example threshold in CO2e units

    # Classify emissions
    if total_co2e > dangerous_threshold:
        st.write("### Classification: Dangerous Emissions")
        st.write("The total CO2e emissions are above the dangerous threshold.")
        st.write("#### Suggested Alternatives:")
        st.write("- Consider using electric vehicles if possible.")
        st.write("- Optimize the route to reduce distance.")
        st.write("- Reduce cargo weight if feasible.")
    else:
        st.write("### Classification: Safe Emissions")
        st.write("The total CO2e emissions are within safe limits.")
        st.write("#### Suggested Alternatives:")
        st.write("- Continue using the current route and vehicle.")
        st.write("- Monitor emissions regularly to ensure they remain within safe limits.")

    # for route in emission_data['route']:
    #     if route['type'] == 'leg':
    #         st.write(f"#### Leg Details")
    #         st.write(f"**Leg CO2e:** {route['co2e']} {route['co2e_unit']}")
    #         st.write(f"**Transport Mode:** {route['transport_mode']}")
    #         st.write(f"**Distance:** {route['distance_km']} km")
    #         st.write(f"**Vehicle Operation CO2e:** {route['vehicle_operation_co2e']} {route['co2e_unit']}")
    #         st.write(f"**Vehicle Energy Provision CO2e:** {route['vehicle_energy_provision_co2e']} {route['co2e_unit']}")

    return emission_data

def calculate_route(waypoints,optimized=False):
    
    st.subheader("AQI Information")
    # Define the city and language for the AQI feed
    city = get_location_from_coordinates(",".join(map(str, waypoints[0])),1)
    lang = "en"

    aqi_js = """

        <script  type="text/javascript"  charset="utf-8">  
    (function  (w,  d,  t,  f)  {  
        w[f]  =  w[f]  ||  function  (c,  k,  n)  {  
            s  =  w[f],  k  =  s['k']  =  (s['k']  ||  (k  ?  ('&k='  +  k)  :  ''));  s['c']  =  
                c  =  (c  instanceof  Array)  ?  c  :  [c];  s['n']  =  n  =  n  ||  0;  L  =  d.createElement(t),  e  =  d.getElementsByTagName(t)[0];  
            L.async  =  1;  L.src  =  '//feed.aqicn.org/feed/'  +  (c[n].city)  +  '/'  +  (c[n].lang  ||  '')  +  '/feed.v1.js?n='  +  n  +  k;  
            e.parentNode.insertBefore(L,  e);  
        };  
    })(window,  document,  'script',  '_aqiFeed');    
    </script>

        <span id="city-aqi-container"></span>  
        <script type="text/javascript" charset="utf-8">  
            _aqiFeed({ display : "%details", container: "city-aqi-container", city: """ + f' "{city}" ' + "});  </script>"
    # Embed the JavaScript code in an HTML component
    print(aqi_js)
    st.components.v1.html(aqi_js, height=200)

    if all(-90 <= wp[0] <= 90 and -180 <= wp[1] <= 180 for wp in waypoints):
        # Format: (latitude, longitude)
        waypoint_query = ":".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
    else:
        # Format: (longitude, latitude)
        waypoint_query = ":".join([f"{wp[1]},{wp[0]}" for wp in waypoints])
    # print(waypoint_query)
    rest_routing_request_url = f'https://atlas.microsoft.com/route/directions/json?subscription-key=97SjjN6bTvmt4Hgg4O8P5cRDWfHkToj7HD4nX6xhDsV8sJkVicajJQQJ99ALAC8vTInPDDZUAAAgAZMP2ojl&api-version=1.0&query={waypoint_query}&routeRepresentation=polyline&travelMode=car&view=Auto'
    print(rest_routing_request_url)
    print("ressss")
    if optimized:
        rest_routing_request_url += '&computeBestOrder=true'
    
    # print(rest_routing_request_url)
    response = requests.get(rest_routing_request_url)
    # print(response.json())
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
    print("result------------")
    print(result)
    calculate_emissions(waypoints, vehicle_options={'vehicleWeight': 1000})
    if optimized:
        pin_order = []
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
    st.write("Enter the coordinates of the waypoints to calculate the optimized route. or else just press the button to see the default waypoints route.")
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
        waypoints = [
    [13.0355, 80.2331],  # T Nagar, Chennai
    [13.0025, 80.2571],  # Adyar, Chennai
    [12.9612, 80.2199],  # Velachery, Chennai
    [13.0827, 80.2090],  # Anna Nagar, Chennai
    [12.9391, 80.1241],  # Tambaram, Chennai
    [13.0105, 80.1728],  # Porur, Chennai
    [13.0032, 80.2504],  # Kotturpuram, Chennai
    [13.0349, 80.2484]   # Alwarpet, Chennai
]



    if st.button("Calculate Waypoint Optimized Route",key='calculate'):
        with st.spinner("Calculating Route..."):
            calculate_route(waypoints, optimized=True)
        # calculate_route(waypoints , optimized=True)
    if st.button("Calculate Route",key='calculate_route'):
        calculate_route(waypoints=waypoints)
        
    
        


waypoint()