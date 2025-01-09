"""
launch_site.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from pathlib import Path
from typing import overload

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

# Translation table for coordinate column names.
# Converts various names to "lat" and "lon".
COORD_COLS_TABLE = str.maketrans(
    {
        "緯度": "lat",
        "経度": "lon",
        "latitude": "lat",
        "longitude": "lon",
    }
)


class launch_site_base(ABC):
    """
    A base class for launch sites.
    """

    def __init__(self):
        self.__sitename: str = ""
        self.__geometry: pd.DataFrame = None
        self.__centroid: Point = None
        self.__is_fall_erea = False

    @abstractmethod
    def GO_NOGO(self, point: Point) -> bool:
        """
        Determines whether the given point is within the safety zone.

        Parameters:
            point (Point):
                The point to check.

        Returns:
            bool:
                True if the point is within the safety zone (GO),
                False if the point is in a prohibited area (NO-GO).
        """
        pass


class safety_zone(launch_site_base):
    def __init__(
        self,
        geometry: pd.DataFrame,
        sitename: str,
    ):
        super().__init__()
        self.__geometry = geometry
        self.__sitename = sitename
        self.__centroid = self.__geometry.centroid

    def GO_NOGO(self, point: Point) -> bool:
        return self.__geometry.contains(point)


class boundary_line(launch_site_base):
    """
    A class representing the boundaries of a prohibited area.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        filepath: Path,
        sitename: str,
    ):
        super().__init__()
        if df is None and filepath is None:
            raise ValueError("Either df or filepath must be specified.")

        if filepath is not None:
            df = pd.read_csv(filepath)

        cols = [col.translate(COORD_COLS_TABLE) for col in df.columns]

        if not {"lat", "lon"} <= cols:
            raise ValueError("The column names are invalid. Must have specific names.")
        if len(df) < 2:
            raise ValueError("The dataframe is empty.")
        self.__geometry = LineString(df[["lon", "lat"]])


@overload
def launch_site(filepath: str | os.PathLike, sitename: str) -> launch_site_base: ...


@overload
def launch_site(df: pd.DataFrame, sitename: str) -> launch_site_base: ...


def launch_site(
    df: pd.DataFrame = None, filepath: str | os.PathLike = None, sitename: str = None
) -> launch_site_base:
    """
    Factory function to create a launch site object.

    Parameters:
        df (pd.DataFrame):
            A dataframe containing the coordinates of the launch site.
        filepath (str | os.PathLike):
            The path to the CSV file containing the coordinates of the launch site.
        sitename (str):
            The name of the launch site.

    Returns:
        launch_site_base:
            The launch site object.
    """
    if df is None:
        df = pd.read_csv(filepath)

    if sitename is None:
        # if the sitename is not specified, use the filename instead
        sitename = filepath.stem

    df.rename(columns=lambda s: s.translate(COORD_COLS_TABLE), inplace=True)
    if not {"lat", "lon"} <= df.columns:
        raise ValueError("The column names are invalid. Must have specific names.")

    if len(df) == 1:
        return
    if len(df) < 2 or df[0] != df[-1]:
        return boundary_line(df, filepath, sitename)
    if len(df) >= 3:
        return safety_zone(df, sitename)
