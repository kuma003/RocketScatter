from __future__ import annotations  # for forward references

import re
from dataclasses import dataclass
from os import PathLike
from typing import List, Optional, Union

from pykml import parser
from shapely.geometry import LineString, Point, Polygon
from tomli_w import dumps


@dataclass
class kml_placemark:
    name: str
    geometry: Union[Point, LineString, Polygon]


@dataclass
class kml_folder:
    name: str
    folders: List[kml_folder]
    placemarks: List[kml_placemark]


def parse_folder(folder: any) -> kml_folder:
    folder_name = folder.name.text if hasattr(folder, "name") else "Unnamed Folder"
    placemarks = []
    folders = []

    for placemark in getattr(folder, "Placemark", []):
        name = (
            placemark.name.text if hasattr(placemark, "name") else "Unnamed Placemark"
        )
        geometry = None

        if hasattr(placemark, "Point"):
            coordinates = placemark.Point.coordinates.text.strip().split(",")
            geometry = Point(float(coordinates[0]), float(coordinates[1]))
        elif hasattr(placemark, "LineString"):
            coordinates = [
                tuple(map(float, coord.strip().split(",")))
                for coord in placemark.LineString.coordinates.text.strip().split()
            ]
            geometry = LineString(coordinates)
        elif hasattr(placemark, "Polygon"):
            coordinates = [
                tuple(map(float, coord.strip().split(",")))
                for coord in placemark.Polygon.outerBoundaryIs.LinearRing.coordinates.text.strip().split()
            ]
            geometry = Polygon(coordinates)

        placemarks.append(kml_placemark(name, geometry))

    child_folders = [parse_folder(child) for child in getattr(folder, "Folder", [])]

    return kml_folder(
        folder_name,
        folders=child_folders,
        placemarks=placemarks,
    )

    if hasattr(folder, "Folder"):
        for child in folder.Folder:
            parse_folder(child, all_folders)


def read_kml(kml_file: PathLike) -> kml_folder:
    with open(kml_file, "r", encoding="utf-8") as file:
        root = parser.parse(file).getroot()
        parse_folder(root.Document)
        return parse_folder(root.Document)


def ask_and_export_mapData_file(
    kml_folders: List[kml_folder], mapData_file_path: PathLike, indent="    "
) -> None:
    """
    Ask user which placemarks to include and export mapData file.

    Args:
        kml_folders (List[kml_folder]): List of kml_folder objects.
        mapData_file_path (PathLike): Path to the output file.
        indent (str, optional): Indentation string. Defaults to "    ".
    """
    exported_data = {"data": []}
    for i, folder in enumerate(kml_folders):
        res = input(f"{i+1}. {folder.name} folder is included? [(y)/n, default is y]: ")
        if not res.lower() in ["y", "yes", ""]:
            continue
        for j, placemark in enumerate(folder.placemarks):
            res = input(
                f"{indent}{i+1}.{j+1}. {placemark.name} is included? [(y)/n, default is y]: "
            )
            if not res.lower() in ["y", "yes", ""]:
                print("")  # empty line
                continue

            if isinstance(placemark.geometry, Polygon):
                coords = list(placemark.geometry.exterior.coords)
            else:
                coords = list(placemark.geometry.coords)

            exported_data["data"] += [
                {
                    "name": placemark.name,
                    "geometry": placemark.geometry.geom_type,
                    "coordinates": coords,
                }
            ]
            if placemark.geometry.geom_type != "Point":
                res = input(
                    f"{indent*2}{placemark.name} is safty area, forbidden area, or not? [s/f/others]: "
                )
                if res.lower() in ["s", "safty"]:
                    exported_data["data"][-1]["type"] = "safty"
                    exported_data["data"][-1][
                        "geometry"
                    ] = "Polygon"  # LineString to Polygon for hit ground point check
                elif res.lower() in ["f", "forbidden"]:
                    exported_data["data"][-1]["type"] = "forbidden"
                    exported_data["data"][-1]["geometry"] = "Polygon"
            print("")  # empty line

    toml_string = dumps(exported_data)

    # toml_string.replace(",\n", "")

    with open(mapData_file_path, "w", encoding="utf-8") as file:
        file.write(toml_string)


def export_mapData_file(
    kml_folders: List[kml_folder], mapData_file_path: PathLike
) -> None:
    """
    Export mapData file without asking user input.\n
    All of the polygons are considered as safty area.

    Args:
        kml_folders (List[kml_folder]): List of kml_folder objects.
        mapData_file_path (PathLike): Path to the output file.
    """
    exported_data = {"data": []}
    for i, folder in enumerate(kml_folders):
        for j, placemark in enumerate(folder.placemarks):
            if isinstance(placemark.geometry, Polygon):
                coords = list(placemark.geometry.exterior.coords)
            else:
                coords = list(placemark.geometry.coords)

            exported_data["data"] += [
                {
                    "name": placemark.name,
                    "geometry": placemark.geometry.geom_type,
                    "coordinates": coords,
                }
            ]
            if placemark.geometry.geom_type == "Polygon":
                exported_data["data"][-1]["type"] = "safty"

    toml_string = dumps(exported_data)

    with open(mapData_file_path, "w", encoding="utf-8") as file:
        file.write(toml_string)
