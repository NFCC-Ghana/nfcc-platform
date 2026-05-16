"""
NFCC CHIRPS Production Ingestion Pipeline (GEE)

Extracts daily CHIRPS rainfall time-series for Accra
using Google Earth Engine.
"""

import ee
import pandas as pd


def init_ee():
    """
    Initialize Google Earth Engine.
    Requires prior authentication using:
        earthengine authenticate
    """
    try:
        ee.Initialize()
        print("Earth Engine initialized successfully.")

    except Exception as e:
        raise RuntimeError(f"Earth Engine initialization failed: {e}") from e


def get_accra_region():
    """
    Define Accra metropolitan bounding box.
    """
    return ee.Geometry.Rectangle([-0.7, 5.3, 0.3, 6.0])


def extract_chirps_timeseries(year=2024):
    """
    Extract daily CHIRPS rainfall statistics for Accra.

    Args:
        year (int): Year to download

    Returns:
        ee.FeatureCollection
    """
    init_ee()

    region = get_accra_region()

    chirps = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .filterBounds(region)
    )

    def extract(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5566,
            maxPixels=1e13,
        )

        return ee.Feature(
            None,
            {
                "date": image.date().format("YYYY-MM-dd"),
                "precip": stats.get("precipitation"),
            },
        )

    features = chirps.map(extract)

    return ee.FeatureCollection(features)


def get_rainfall_timeseries(year=2024):
    """
    Convert CHIRPS FeatureCollection to pandas DataFrame.

    Args:
        year (int): Year to retrieve

    Returns:
        pandas.DataFrame
    """
    fc = extract_chirps_timeseries(year)

    dates = fc.aggregate_array("date").getInfo()
    precip = fc.aggregate_array("precip").getInfo()

    df = pd.DataFrame(
        {
            "date": dates,
            "precipitation": precip,
        }
    )

    df["date"] = pd.to_datetime(df["date"])

    # Remove null precipitation values
    df = df.dropna()

    return df


if __name__ == "__main__":
    print("Downloading CHIRPS rainfall data for Accra...")

    rainfall_df = get_rainfall_timeseries(2024)

    print(f"Downloaded {len(rainfall_df)} " "days of rainfall data.")

    print(rainfall_df.head())

    rainfall_df.to_csv(
        "data/processed/chirps_accra_2024.csv",
        index=False,
    )

    print("CSV file saved successfully.")
