import base64
import json
import time
import random


import plasma
from plasma import plasma_stick
import urequests as requests

import WIFI_CONFIG
from network_manager import NetworkManager
import uasyncio

# Read config file
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

access_token = None

# Set up the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(
    int(config["num_leds"]), 0, 0,
    plasma_stick.DAT,
    color_order=plasma.COLOR_ORDER_RGB)



#------------------------------------------#
# Light related functions

def status_handler(mode, status, ip):
    # reports wifi connection status
    print(mode, status, ip)
    print('Connecting to wifi...')
    # flash while connecting
    for i in range(config["lighting"]["num_leds"]):
        led_strip.set_rgb(i, 255, 255, 255)
        time.sleep(0.02)
    for i in range(config["lighting"]["num_leds"]):
        led_strip.set_rgb(i, 0, 0, 0)
    if status is not None:
        if status:
            print('Wifi connection successful!')
        else:
            print('Wifi connection failed!')
            # if no wifi connection, pulse red (error)
            error()

def error(): # Pulses red to indicate an error
    print("Error")
    
    from math import sin
    COLOUR = 0.0


    # start updating the LED strip
    led_strip.start()

    offset = 0

    while True:
        # use a sine wave to set the brightness
        for i in range(config["num_leds"]):
            led_strip.set_hsv(i, COLOUR, 1.0, sin(offset))
        offset += 0.002

def clear(): # Clears the LED strip
    print("Clear")
    for i in range(config["lighting"]["num_leds"]):
        led_strip.set_rgb(i, 0, 0, 0)

def idle():
    print("Idle")
    
    if config["lighting"]["idle"]["idle_set_by_pfp"] == True:
        print("Idle set by pfp")
        return
    
    else:
        idle_colours = config["lighting"]["idle"]["manual_colours"]
        for i in range(config["lighting"]["num_leds"]):
            led_strip.set_rgb(i, int(idle_colours[0]), int(idle_colours[1]), int(idle_colours[2]))

def lerp_color(color1, color2, t): # Gradually changes between two colours using 'linear interpolation'
    return (
        int(color1[0] * (1 - t) + color2[0] * t),
        int(color1[1] * (1 - t) + color2[1] * t),
        int(color1[2] * (1 - t) + color2[2] * t)
    )
    
def fade_colors(colors, steps):
    for i in range(len(colors) - 1):
        for t in range(steps):
            t /= steps
            yield lerp_color(colors[i], colors[i+1], t)

#------------------------------------------#

def get_cache():
    with open("cache.json", "r", encoding="utf-8") as cache_file:
        cache = json.load(cache_file)
        
    return cache

def write_cache(cache):
    with open("cache.json", "w", encoding="utf-8") as cache_file:
        json.dump(cache, cache_file, indent=4) #remove indent=4 for production to save space


def refresh_token():
    global access_token
    
    url = "https://accounts.spotify.com/api/token"

    # Replace with your client id and client secret
    client_id = config["spotify"]["client_id"]
    client_secret = config["spotify"]["client_secret"]

    # Base64 encode the client id and client secret
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()


    headers = {
        "Authorization": f"Basic {encoded}",
        'Content-type': 'application/x-www-form-urlencoded', 
    }


    params = {
        "grant_type": 'refresh_token',
        "refresh_token": config["spotify"]["refresh_token"],
        "client_id": "292fdb035a69497f845bda1145279903",
    }

    response = requests.post(url, headers=headers, params=params)
    print("Refreshed token")
    
    if response.status_code != 200:
        print(response.status_code)
        print("Failed to get access token")
        error()

    access_token = {
    "access_token": response.json()["access_token"],
    "created_at": time.time(),
    }
    
    return access_token["access_token"]

def get_token():
    print("Getting token")
    # Get a new token if there is no token or if the token is expired
    if not access_token or (time.time() - access_token["created_at"]) > 3600:
        return refresh_token()
    
    # Otherwise, return the current access_token
    return access_token["access_token"]

def get_currently_playing_album_art():
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    
    headers = {
        "Authorization": f"Bearer {get_token()}",
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 204:
        print("No song currently playing")
        return None

    if response.status_code == 429:
        print("Rate limited")
        return None
    
    if response.status_code != 200:
        print(response.status_code)
        print("Failed to get currently playing")
        
        error()
    
    data = response.json()
    
    return data["item"]["album"]["images"][0]["url"]
    

def get_colours_from_image(img_url):
    print("Getting colours from image: " + img_url)
    req_url  = "https://api.imagga.com/v2/colors"
    
    params = {
        "image_url": img_url,
        "seperated_count": int(config["imagga"]["number_of_colours"]),
        "extract_object_colors": "0",
    }
    
    api_key = config["imagga"]["api_key"]
    api_secret = config["imagga"]["api_secret"]
    
    response = requests.get(req_url, params=params, auth=(api_key, api_secret))
    
    if response.status_code != 200:
        print(response.status_code)
        print("Failed to get colours")
        error()

    data = response.json()["result"]
    list_of_colours = []
    
    for colour in data["colors"]["image_colors"]:
        list_of_colours.append({
            "r" : colour["r"],
            "g" : colour["g"],
            "b" : colour["b"],
            "percent" : colour["percent"]
            }
        )
        
    return list_of_colours

def update_cache():
    print("Updating cached playlist images")
    for playlist in config["spotify"]["cached_playlist_ids"]:
        url = f"https://api.spotify.com/v1/playlists/{playlist}/tracks"
        
        headers = {
            "Authorization": f"Bearer {get_token()}",
        }
        
        params = {
            "market": config["spotify"]["market"],
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        print(response.status_code)
        
        if response.status_code != 200:
            print("Failed to get playlist")
            error()
        
        data = response.json()
        
        cache = get_cache()
            
        for entry in data["items"]:
            album_cover_url = entry["track"]["album"]["images"][0]["url"]
            
            try:
                cache[album_cover_url]
            
            except KeyError:
                colours = get_colours_from_image(album_cover_url)
                
                cache[album_cover_url] = {"colours" : colours, "req_count" : 0}
                
                print(f"Added {album_cover_url} to cache")
            
        write_cache(cache)

def check_cache_size():
    cache = get_cache()
        
    if len(cache) > config["cache"]["size"]:
        print("Cache too big, clearing")

        old_cache = cache.copy()
        for entry in old_cache:
            if cache[entry]["req_count"] < config["cache"]["min_req_count"]:
                del cache[entry]
        
        write_cache(cache)
    
    else:
        print("Cache healthy {} entries".format(len(cache)))
             

def get_values(img_url):
    cache = get_cache()
        
    if img_url == None:
        return None
        
    try:
        colours = cache[img_url]["colours"]
    
    except KeyError:
        print("Image not in cache")
        check_cache_size() # Check cache size before adding new entry
        
        colours = get_colours_from_image(img_url)
        
        cache[img_url] = {"colours" : colours, "req_count" : 0}
        
        print(f"Added {img_url} to cache")
        
        write_cache(cache)
            
        return colours
    
    cache[img_url]["req_count"] += 1
    
    write_cache(cache)
    
    return colours

       
'''     
#------------------------------------------#
# Setup network

try:
    network_manager = NetworkManager(WIFI_CONFIG.COUNTRY, status_handler=status_handler)
    uasyncio.get_event_loop().run_until_complete(network_manager.client(WIFI_CONFIG.SSID, WIFI_CONFIG.PSK))
except Exception as e:
    print(f'Wifi connection failed! {e}')
    # if unable to connect to wifi, pulse red (error)
    error()
     
#setup
'''

update_cache()
check_cache_size()
    
currently_idle = False

while True:
        
    current_playing = get_currently_playing_album_art()
    time_of_last_update = time.time()
    
    if current_playing is None:
        if not currently_idle:
            print("No song currently playing")
            #idle()
            currently_idle = True
        time.sleep(config["lighting"]["update_interval"])
        continue
    last_playing = None
    if currently_idle == True:
        #clear()
        currently_idle = False
        
    colour_values = get_values(current_playing)
            
    for colour in fade_colors(colour_values, config["lighting"]["fade_steps"]):
        for i in range(config["lighting"]["num_leds"]):
            led_strip.set_rgb(i, colour[0], colour[1], colour[2])
            time.sleep(0.01)
        
        if time.time() - time_of_last_update > config["lighting"]["update_interval"]:
            if current_playing != get_currently_playing_album_art():
                break
        
    
    print(current_playing)
    time.sleep(config["lighting"]["update_interval"])
    