#!/usr/bin/env python3

import json
import requests
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

def geocode_location(location, api_key):
    """Perform the geocoding request using Google Maps Geocoding API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to perform geocoding: {response.text}")
        return None

def process_json(input_file, output_file, api_key):
    """Read the input JSON, perform geocoding, and save the updated JSON."""
    try:
        with open(input_file, 'r') as infile:
            data = json.load(infile)
        
        district = data['label']['district']
        geographic_info = data['extracted_metadata'].get('Geographic_information', '')
        location_query = f"{geographic_info}, {district} District, Zimbabwe"
        
        logger.info(f"Geocoding location: {location_query}")
        geocoding_result = geocode_location(location_query, api_key)
        
        if geocoding_result:
            data['geocoding'] = geocoding_result
        
        with open(output_file, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        logger.info(f"Updated JSON saved to {output_file}")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Perform geocoding using the Google Maps API.')
    parser.add_argument('input_file', help='Input JSON file')
    parser.add_argument('output_file', help='Output JSON file')
    parser.add_argument('--api_key', required=True, help='Google Maps Geocoding API Key')
    
    args = parser.parse_args()
    process_json(args.input_file, args.output_file, args.api_key)

if __name__ == '__main__':
    main()