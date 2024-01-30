import streamlit as st
import pandas as pd
import googlemaps
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Evénements à Paris")

#### API #####################################################

api_key = 'AIzaSyA9099__3A5Tw8PPH6mTEVp72m7YFO-TJk'
gmaps = googlemaps.Client(key=api_key)


### functions to estimate time and details ###################

def extract_transit_details(api_response):
    train_count = 0
    train_details = []
    subway_count = 0
    subway_details = []
    bus_count = 0
    bus_details = []
    tram_count = 0
    tram_details = []

    for leg in api_response[0]['legs']:
        for step in leg['steps']:
            if 'transit_details' in step and 'line' in step['transit_details']:
                line_details = step['transit_details']['line']
                if line_details['vehicle']['type'] == 'HEAVY_RAIL':
                    train_count += 1
                    train_details.append(f"Train: {train_count}, line: {line_details['name']}")
                elif line_details['vehicle']['type'] == 'SUBWAY':
                    subway_count += 1
                    subway_details.append(f"Subway: {subway_count}, line: {line_details['name']}")
                elif line_details['vehicle']['type'] == 'BUS':
                    bus_count += 1
                    bus_details.append(f"Bus: {bus_count}, line: {line_details['name']}")
                elif line_details['vehicle']['type'] == 'TRAM':
                    tram_count += 1
                    tram_details.append(f"Tram: {tram_count}, line: {line_details['name']}")
                
    return train_details, subway_details, bus_details, tram_details


def get_estimated_time_bicycling(origin, destination, departure_time="now"):
    mode = 'vélo'
    directions_result = gmaps.directions(
        origin,
        destination,
        mode="bicycling",
        departure_time=departure_time
    )
    
    duration = directions_result[0]['legs'][0]['duration']['value']//60 # in minutes
    distance = directions_result[0]['legs'][0]['distance']['value']/1000 # in km
    
    # estimations, true values would depend on a lot of factors
    calories = 23*distance # spent calories in kcal
    
    return (duration, distance, calories)


def get_estimated_time_walking(origin, destination, departure_time="now"):
    mode = 'à pieds'
    directions_result = gmaps.directions(
        origin,
        destination,
        mode="walking",
        departure_time=departure_time
    )
    
    duration = directions_result[0]['legs'][0]['duration']['value']//60 # in minutes
    distance = directions_result[0]['legs'][0]['distance']['value']/1000 # in km
    
    # estimations, true values would depend on a lot of factors
    calories = 50*distance # spent calories in kcal

    return (duration, distance, calories)


def get_estimated_time_driving(origin, destination, departure_time="now"):
    mode = 'voiture'
    directions_result = gmaps.directions(
        origin,
        destination,
        mode="driving",
        departure_time=departure_time
    )
    
    # we return the estimated duration in minutes taking into account the possible traffic
    # by default the 'traffic_model' parameter's value is 'best_guess', using this the returned duration_in_traffic 
    # is the best estimate of travel time given what is known about both historical traffic conditions and 
    # live traffic. Live traffic becomes more important the closer the departure_time is to now.
    duration = directions_result[0]['legs'][0]['duration_in_traffic']['value']//60 # in minutes
    
    distance = directions_result[0]['legs'][0]['distance']['value']/1000 # in km
    
    # estimations, true values would depend on a lot of factors
    conso_essence = distance*7.54/100 # consumption for oil cars in L
    conso_diesel = distance*6.11/100 # consumption for diesel cars in L
    
    price_essence = conso_essence*1.965 # cost of the consummed oil in €
    price_diesel = conso_diesel*1.982 # cost of the consummed diesel in €
    
    co2_essence = conso_essence*2280/1000 # CO2 emissions for the trip in kg
    co2_diesel = conso_diesel*2670/1000 # CO2 emissions for the trip in kg

    return (duration, distance, conso_essence, conso_diesel, price_essence, price_diesel, co2_essence, co2_diesel)


def get_estimated_time_transit(origin, destination, departure_time="now"): # transit => public transports
    mode = 'transports en commun'
    directions_result = gmaps.directions(
        origin,
        destination,
        mode="transit",
        departure_time=departure_time
    )
    
    duration = directions_result[0]['legs'][0]['duration']['value']//60 # in minutes
    distance = directions_result[0]['legs'][0]['distance']['value']/1000 # in km
    transit_details = extract_transit_details(directions_result)
    
    # estimations, true values would depend on a lot of factors
    co2 = distance*29 # CO2 emissions for the trip in kg (average between all means of transport)
    # could be way less if the trip does not include bus
    
    # We return the estimated duration in minutes and the details of the route
    return (duration, distance, co2, transit_details)

####################################################################

csv_url = "https://raw.githubusercontent.com/acharruey/Webscraping_S9/95e02efbe3af5abb9be740b34dc3eaadde0218bc/shotgun_dice_datas.csv"
df = pd.read_csv(csv_url)

html_style = """
<style>
    body {
        font-family: 'Space Grotesk', sans-serif;
        background-color: rgb(27, 27, 27);
        margin: 0;
        padding: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    h1 {
        text-align: center;
        color: whitesmoke;
        margin-bottom: 20px;
    }

    label {
        display: block;
        color: whitesmoke;
        margin-bottom: 10px;
    }

    #startAddress {
        padding: 10px;
        font-size: 1em;
        width: 50%;
        box-sizing: border-box;
        margin-bottom: 20px;
        border: 1px solid #666;
        border-radius: 5px;
        background-color: #1B1B1B;
        color: #999;
    }

    #eventsContainer {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        margin-top: 20px; 
    }

    .event {
        width: 300px;
        margin: 20px;
        padding: 15px;
        background-color:#1B1B1B;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease-in-out;
        cursor: pointer;
    }

    .event:hover {
        transform: scale(1.05);
    }

    h2 {
        color: whitesmoke;
        font-size: 1.5em;
        margin-bottom: 10px;
    }

    .event h2 {
        color: whitesmoke;
        font-size: 1.5em;
        margin-bottom: 10px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    p {
        color: #999;
        margin: 3px 0; 
    }

    strong {
        color: #666;
    }

    button {
        font-size: 1.5em;
        font-family: 'Space Grotesk', sans-serif;
        padding: 10px 20px;
        background-color: #444;
        color: black;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s ease-in-out;
        align-self: center;
    }

    button:hover {
        background-color: #fff;
    }

    .hidden {
        display: none;
    }

    #loadButton {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: fadeInUp 1s ease-in-out;
    }

    @keyframes fadeInUp {
        0% {
            opacity: 0;
            transform: translate(-50%, -60%);
        }
        100% {
            opacity: 1;
            transform: translate(-50%, -50%);
        }
    }

    .artists {
        display: inline-block;
        padding: 4px;
        margin-right: 4px;
        margin-bottom: 4px;
        background-color: #222;
        border-radius: 4px;
        color: #999; 
    }

    .genres {
        display: inline-block;
        padding: 4px;
        margin-right: 4px;
        margin-bottom: 4px;
        background-color: #222;
        border-radius: 4px;
    }
</style>
"""

st.markdown(html_style, unsafe_allow_html=True)


st.title("Événements à Paris")

start_address = st.text_input("Entrez votre adresse de départ :")
chosen_mode = st.radio('Mode de transport :', options=['à pieds', 'vélo', 'voiture', 'transports en commun'], horizontal=True)

if st.button("Calculer le temps de trajet"):
    st.markdown("---")

    for index, row in df.iterrows():
        destination = row['Location']

        if chosen_mode  == "transports en commun":
            estimated_time, distance, co2, transit_details = get_estimated_time_transit(start_address, destination)
        elif chosen_mode == 'voiture':
            estimated_time, distance, conso_essence, conso_diesel, price_essence, price_diesel, co2_essence, co2_diesel = get_estimated_time_driving(start_address, destination)
        elif chosen_mode == 'vélo':
            estimated_time, distance, calories = get_estimated_time_bicycling(start_address, destination)
        elif chosen_mode == 'à pieds':
            estimated_time, distance, calories = get_estimated_time_walking(start_address, destination)
        
        st.markdown(f"## {row['Event Title']}")
        st.write(f"Le {row['Date']} de {row['Heure']}")
        if not pd.isnull(row['Organizer']):
            st.write(f"Par {row['Organizer']}")
            
        st.markdown(" ")

        if not pd.isnull(row['Artists']):
            st.markdown(f"**Line-up :** {', '.join([f'**{artist}**' for artist in row['Artists'].split(', ')])}")

        if not pd.isnull(row['Genres']):
            genres_html = ', '.join([f'{genre.upper()}' for genre in row['Genres'].split(',')])
            st.markdown(f"**Genres :** {genres_html}", unsafe_allow_html=True)

        if not pd.isnull(row['Venue Name']) and not pd.isnull(row['Location']):
            st.markdown(" ")
            st.write(f"{row['Venue Name']} | {row['Location']}")

        if not pd.isnull(row['Price']):
            st.write(f"A partir de {row['Price']}")

        st.markdown(" ")
        st.write("Trajet :")

        if chosen_mode == 'transports en commun':
            if transit_details[0]:  
                st.write(f"Trains: {', '.join(transit_details[0])}")

            if transit_details[1]:  
                st.write(f"Métro: {', '.join(transit_details[1])}")

            if transit_details[2]:  
                st.write(f"Bus: {', '.join(transit_details[2])}")

            if transit_details[3]:  
                st.write(f"Tram: {', '.join(transit_details[3])}")

        if chosen_mode == 'transports en commun':
            st.write(f"Temps de trajet : {estimated_time} minutes")
            st.write(f"Distance: {distance}km | CO2: {np.round(co2,2)}kg")

        elif chosen_mode == 'à pieds':
            st.write(f"Temps de trajet : {estimated_time} minutes")
            st.write(f"Distance: {distance}km | Calories: {calories}kcal")

        elif chosen_mode == 'vélo':
            st.write(f"Temps de trajet : {estimated_time} minutes")
            st.write(f"Distance: {distance}km | Calories: {calories}kcal")

        elif chosen_mode == 'voiture':
            st.write(f"Temps de trajet : {estimated_time} minutes")
            st.write(f"Distance: {distance}km")
            st.write(f"Consommation essence : {np.round(conso_essence,2)}L | Prix essence : {np.round(price_essence,2)}€ | CO2 essence  : {np.round(co2_essence,2)}kg")
            st.write(f"Consommation diesel : {np.round(conso_diesel,2)}L | Prix diesel : {np.round(price_diesel,2)}€ | CO2 diesel  : {np.round(co2_diesel,2)}kg")
        st.markdown("---")
        
for index, row in df.iterrows():
    st.markdown(f"## {row['Event Title']}")
    st.write(f"Le {row['Date']} de {row['Heure']}")
    if not pd.isnull(row['Organizer']):
        st.write(f"Par {row['Organizer']}")
        
    st.markdown(" ")

    if not pd.isnull(row['Artists']):
        st.markdown(f"**Line-up :** {', '.join([f'**{artist}**' for artist in row['Artists'].split(', ')])}")

    if not pd.isnull(row['Genres']):
        genres_html = ', '.join([f'{genre.upper()}' for genre in row['Genres'].split(',')])
        st.markdown(f"**Genres :** {genres_html}", unsafe_allow_html=True)

    if not pd.isnull(row['Venue Name']) and not pd.isnull(row['Location']):
        st.markdown(" ")
        st.write(f"{row['Venue Name']} | {row['Location']}")

    if not pd.isnull(row['Price']):
        st.write(f"A partir de {row['Price']}")

    st.markdown("---")
