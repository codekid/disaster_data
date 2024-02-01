import inspect
import os
import shutil

import pandas as pd
import gzip
import urllib.request
from bs4 import BeautifulSoup
from structlog import get_logger


URL = "https://www1.ncdc.noaa.gov/pub/data/swdi/stormevents/csvfiles/"


# import psycopg2
def get_function_name() -> str:
    """
    Return the calling function name
    """
    return inspect.stack()[1][3]


logger = get_logger()


def get_file_data(url: str, filename: str, dest_dir: str) -> None:
    """
    Pulls the data from the address and appends it to the file
    """
    url = url + filename
    # Open url to file
    logger.info(get_function_name(), message=f"Attempting to extract {filename}.")
    response = urllib.request.urlopen(url)
    destination_file = f"{dest_dir}/{filename[:-3:]}"
    # Append data to output
    with open(destination_file, "ab") as outfile:
        # Skip the first line of the file and write the others to the output file
        # next(f)
        outfile.write(gzip.decompress(response.read()))

    logger.info(get_function_name(), message=f"Successfully extract {filename}.")


def get_filenames(soup, filenames) -> list:
    """
    Get the names of the files on the website and store them in a list
    """
    logger.info(get_function_name(), message="Extracting list of file names.")
    # Find all the <a> tags, extract the file names and add them to a list
    # for files in soup.find_all("a", limit=10):
    for files in soup.find_all("a"):
        # print (files.text.strip())
        if "details-ftp" in files.text:
            file_name = files.text.strip()
            filenames.append(file_name)

    num_files = len(filenames)
    logger.info(
        get_function_name(),
        message=f"File name extraction complete",
    )
    return filenames


def check_directory_exists(directory: str) -> None:
    """
    Check if the directory exists
    """
    if os.path.exists(directory):
        logger.info(get_function_name(), message=f"{directory} folder already exists.")
    else:
        logger.info(
            get_function_name(),
            message=f"Folder does not exist, now creating {directory} folder.",
        )
        os.mkdir(directory)


def get_weather_data_page() -> BeautifulSoup:
    """
    Get the web page for the weather data
    """
    logger.info(get_function_name(), message="Preparing to get the url")
    result = urllib.request.urlopen(URL)
    logger.info(get_function_name(), message="Retrieval complete!")
    raw_html = result.read()
    soup = BeautifulSoup(raw_html, "html.parser")

    return soup


def move_file(file: str, source_dir: str, dest_dir: str) -> None:
    """Moves files to a new directory"""
    raw_file_location = f"{source_dir}/{file}"
    archive_file_location = f"{dest_dir}/{file}"
    logger.info(get_function_name(), message=f"{file} from {source_dir} to {dest_dir}")
    shutil.move(raw_file_location, archive_file_location)


def check_already_loaded(files, conn) -> list:
    loaded_sql = "SELECT DISTINCT __filename FROM disaster_data_log"
    logger.info(
        get_function_name(), message=f"Running the following query: {loaded_sql}"
    )
    loaded_files = pd.read_sql(loaded_sql, conn)
    loaded_files = loaded_files["__filename"].values.tolist()

    return loaded_files


def main(filenames=None):
    """Main landing area."""

    if filenames is None or len(filenames) == 0:
        filenames = []

        soup = get_weather_data_page()

        filenames = get_filenames(soup, filenames)

    base_dir = os.getcwd()
    dest_dir = base_dir + "/raw"
    archive_dir = base_dir + "/archive"
    os.chdir(base_dir)

    check_directory_exists(dest_dir)
    check_directory_exists(archive_dir)

    for c, filename in enumerate(filenames):
        get_file_data(url=URL, filename=filename, dest_dir=dest_dir)

    logger.info(get_function_name(), messsage="Extraction Successful.")


if __name__ == "__main__":
    main()
