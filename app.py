from flask import Flask, request, Response # https://flask.palletsprojects.com/en/2.0.x/quickstart/
# Flask is a lightweight WSGI web application framework. 
# https://wsgi.readthedocs.io/en/latest/what.html

import os # only used here for accessing env vars
# https://docs.python.org/3/library/os.html

from functools import wraps # https://docs.python.org/3/library/functools.html#functools.wraps
# wraps enables use of function decorators

# Download the twilio-python library from twilio.com/docs/python/install
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Conference, Dial, Say, Gather, Record, Leave, Hangup, Pay, Prompt, Connect

from hashlib import sha1, sha256 # https://docs.python.org/3/library/hashlib.html
# This module implements a common interface to many different secure hash and message digest algorithms.

import hmac # https://docs.python.org/3/library/hmac.html
# This module implements the HMAC algorithm as described by RFC 2104.
# HMAC - hash-based message authentication code

import base64 # https://docs.python.org/3/library/base64.html
# This module provides functions for encoding binary data to printable ASCII characters 
# and decoding such encodings back to binary data. 

import requests # https://docs.python-requests.org/en/latest/
# used for sending HTTP requests

import us # https://pypi.org/project/us/
# used for working with US state metadata

import re # https://docs.python.org/3/library/re.html
# used for regex operations

import datetime # https://docs.python.org/3/library/datetime.html
# used to work with dates

from random import randrange # https://docs.python.org/3/library/random.html#random.randrange
# enables random number selection from a defined range


# GLOBAL VAR 
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# instantiate flask class
# https://flask.palletsprojects.com/en/2.0.x/api/#flask.Flask
app = Flask(__name__)

# signature validation decorator using Twilio helper library
# https://flask.palletsprojects.com/en/2.0.x/patterns/viewdecorators/
def validate_twilio_request():
    def extra(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            validator = RequestValidator(TWILIO_AUTH_TOKEN)
            https_url = 'https://' + request.url.lstrip('http://') # request.url shows http when https is used, so we need to fix it
            twilio_signature = request.headers.get('X-Twilio-Signature')
            params = request.form
            if not twilio_signature:
                return Response('No signature', 500)  
            elif not validator.validate(https_url, params, twilio_signature):
                return Response('Incorrect signature', 403)
            return f(*args, **kwargs)
        return decorated
    return extra

@app.route("/twiml", methods=['POST'])
def twiml():
    # if no X-Twilio-Signature header exists, reject the request
    try:
        twil_sig = request.headers['X-Twilio-Signature']
        print(f"X-Twilio-Signature: {twil_sig}")
    except KeyError:
        return('No X-Twilio-Signature. This request likely did not originate from Twilio.', 418) # since we are 'home brewing' this validation, a 418 seems apropos
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/418
    
    # If the X-Twilio-Signature header does exist, then let's follow the steps outlined in the docs:
    # https://www.twilio.com/docs/usage/security#validating-requests
    #
    # 1. Take the full URL of the request URL you specify for your phone number or app, from the protocol (https...) through the end of the query string (everything after the ?).
    #   Side note:
    #       using ngrok, the url is http, but the request is sent over https. We need to make it match to calculate the correct signature. 
    #       if your request.url already references https, just use domain = request.url instead
    domain = re.sub('http', 'https', request.url) 

    # 2. If the request is a POST, sort all of the POST parameters alphabetically (using Unix-style case-sensitive sorting order).
    # 3. Iterate through the sorted list of POST parameters, and append the variable name and value (with no delimiters) to the end of the URL string.
    #   Side Note:
    #       As an additional protective measure against request forgeries, we should reject requests without any form params
    if request.form:
        for k, v in sorted(request.form.items()):
            domain += k + v
    else:
        return ('Bad Request - no form params', 400) # HTTP 400 Bad Request - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
   
    # 4. Sign the resulting string with HMAC-SHA1 using your AuthToken as the key (remember, your AuthToken's case matters!).
    mac = hmac.new(bytes(TWILIO_AUTH_TOKEN, 'UTF-8'), domain.encode("utf-8"), sha1)
    print(mac.__dict__)
    print(mac.digest())

    # 5. Base64 encode the resulting hash value.
    computed = base64.b64encode(mac.digest()) 
    print(f"computed value (base64 encoded): {computed}")
    computed = computed.decode('utf-8') # still binary, so let's make it readable??
    print(f"computed value (utf-8 decoded): {computed}")
    diy_signature = computed.strip() # strip() removes any leading and trailing spaces - https://www.w3schools.com/python/ref_string_strip.asp
    print(f"diy_signature value: {diy_signature}")

    # 6. Compare your hash to the one provided by Twilio in the X-Twilio-Signature header. If they match, then you're good to go.
    if diy_signature != twil_sig:
        return ('Signature does not match', 403) # HTTP 403 Forbidden - https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
    else:
        twiml_response = "<Response><Say>Huzzah! The Signature has been validated!</Say></Response>" # no helper libs, so TwiML preprocessing :(
        return Response(twiml_response, mimetype='application/xml')


@app.route("/decorator_test", methods=['POST'])
@validate_twilio_request()
def decorator_test():
    r = VoiceResponse()
    r.say("Signature is validated!")
    return Response(str(r), mimetype='application/xml')


@app.route("/weather", methods=['POST'])
#@validate_twilio_request()
def weather():
    print('-' * 55)
    # First, let's pull the location info from the incoming call webhook
    # https://www.twilio.com/docs/usage/webhooks/voice-webhooks#incoming-voice-call
    # https://www.twilio.com/docs/voice/twiml#twilios-request-to-your-application
    try:
        city = request.form['CallerCity']
        state = request.form['CallerState']
        country = request.form['CallerCountry']

    # Sometimes, this information is not available, so we should set some defaults. 
    # Instead of defaults, you could return TwiML that says "Sorry, your location cannot be determined/"
    # Or, implement some kind of DTMF City/ zip code entry system. 
    except:
        r = randrange(50)
        s = us.states.STATES[r]
        state = us.states.lookup(str(s))
        city = str(state.capital)
        state = str(state)
        country = "US"

    # the open weather API's current weather endpoint requires a lat/long coordinates
    # so we use their geolocator endpoint to determine the coordinates of our given city, state, country. 
    geofinder = requests.get(f'http://api.openweathermap.org/geo/1.0/direct?q={city},{state},{country}&limit=100&appid={WEATHER_API_KEY}')
    print(f"{datetime.datetime.now()} - Geo Finder Status Code: {geofinder.status_code}")
    if geofinder.status_code != 200:
        print(f"{datetime.datetime.now()} - ERROR!!!!! :-(")
        print(f"{datetime.datetime.now()} - Geo Finder Status Code: {geofinder.status_code}")
        return("Not OK", geofinder.status_code)
    geo_data = geofinder.json()
    for g in geo_data:
        # The geo locator API returns a full state name, but Twilio's CallerState is the abbreviation. 
        # the us library provides an easy way to normalize the State values for comparison. 
        if g['state'] == us.states.lookup(state).name:
            lat = g['lat']
            lon = g['lon']

            w = requests.get(f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=imperial&appid={WEATHER_API_KEY}')
            print(f"{datetime.datetime.now()} - Weather Status Code: {w.status_code}")
            if w.status_code != 200:
                print(f"{datetime.datetime.now()} - ERROR!!!!! :-(")
                print(f"{datetime.datetime.now()} - Weather Status Code: {w.status_code}")
                return("Not OK", w.status_code)
            w_data = w.json()
            temp = w_data['main']['temp']
            break

    # use all the data from above to construct our TwiML <Say> response.         
    twiml_response = f"<Response><Say>Thank you for calling the weather hotline. The temperature in {city}, {g['state']} is {temp} degrees. </Say></Response>"
    print(f"Temp in {city}, {state}: {temp}")
    return Response(twiml_response, mimetype='application/xml')


if __name__ == '__main__':
    app.run(debug=True, port=3030, host="0.0.0.0")
    print("Server listening on: http://localhost:" + str(3030))
