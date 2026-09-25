''' Code for geocoding placenames '''
import argparse
import json
from collections import Counter
import pandas as pd
import geopandas as gpd
import googlemaps
from config import GMAPS_API_KEY

gmaps = googlemaps.Client(key=GMAPS_API_KEY)


def load_json(filename):
    ''' Code for loading a json file '''
    with open(filename, encoding='utf-8') as f:
        d = json.load(f)
        return d


def save_json(filename, data):
    ''' Code for saving a json file '''
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data(csvs):
    ''' to load one or many csvs '''
    return pd.concat(
        [pd.read_csv(csv) for csv in csvs],
        ignore_index=True
    )

def geocode(placename, cache, gmaps_key):
    ''' This function is to geocode the place names '''
    print(placename)
    # check if placename is not already geocoded
    if placename not in cache:
        print(" --- placename not in cache, geocoding... --- ")
        geocode_result = gmaps_key.geocode(placename)
        if geocode_result:
            latlon = geocode_result[0]['geometry']['location']
            cache[placename] = latlon
            return latlon
        else:
            return None
    else:
        print(" --- placename already in cache --- ")
        return cache[placename]

def geocode_runner(df, cache):
    ''' prep df and run geocode over df '''
    # Get all geographic placenames
    placenames = [
        x.strip()
        for x in ";".join(df["geographic"].dropna()).split(";")
        if x.strip()
    ]
    # Count how many times each place is mentioned
    mention_counts = pd.Series(placenames).value_counts()
    # Remove duplicates for geocoding
    placenames = list(dict.fromkeys(placenames))
    # Geocode each unique place
    results = [geocode(x, cache, gmaps) for x in placenames]
    # Create DataFrame
    geodf = pd.DataFrame({
        "location": placenames,
        "mentions": [mention_counts[x] for x in placenames],
        "lat": [x["lat"] if x else None for x in results],
        "lon": [x["lng"] if x else None for x in results]
    })
    # Save to CSV
    geodf.to_csv(
        'output_data/geocoded_locations.csv',
        index=False
    )
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        geodf,
        geometry=gpd.points_from_xy(
            geodf["lon"],
            geodf["lat"]
        ),
        crs="EPSG:4326"
    )
    # Save GeoJSON
    gdf.to_file(
        'output_data/geocoded_locations.geojson',
        driver='GeoJSON'
    )
    # Save geocoding cache
    save_json('geocache.json', cache)

def count_runner(df, column_name, threshold, filename):
    ''' function to transform data for bar graphs'''
    terms = {
            term: count
            for term, count in Counter(
                x.strip()
                for x in ";".join(df[column_name].dropna()).split(";")
                if x.strip()
            ).items()
            if count >= threshold
        }
    save_json(filename, terms)


def main():
    ''' Main function for calling script on its own. '''
    parser = argparse.ArgumentParser(description='Geocode locations')
    parser.add_argument("csvs", nargs="+")
    parser.add_argument(
        'cache',
        help='JSON of geolocated entities'
    )
    args = parser.parse_args()
    cache = load_json(args.cache)
    
    df = load_data(args.csvs)
    # run code for geocoding
    geocode_runner(df, cache)
    # run code for heatmap
    # start graphing logic
    count_runner(df, 'geographic', 3, 'output_data/bargraphdata.json')
    count_runner(df, 'subject', 5, 'output_data/subjectdata.json')



if __name__ == "__main__":
    main()
