from pprint import pprint

from src.rocket_scatter import kml_reader

if __name__ == "__main__":
    kml_folders = kml_reader.read_kml("ISE26th.kml")
    kml_reader.ask_and_export_mapData_file(kml_folders, "mapData.toml")
