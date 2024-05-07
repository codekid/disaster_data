from ...dags.scripts.disaster_data.disaster_data_extraction import (
    remove_invalid_rows,
    add_meta_cols,
)
from pandas import DataFrame
import pandas as pd


def test_remove_invalid_data() -> None:
    """Testing the removal invalid rows
    In some files, the column headers appear at random spots
    other than the top. We're testing if the function to remove
    them works.
    """
    data = pd.read_csv("./tests/samples/sample_weather_data.csv")
    clean_data = remove_invalid_rows(data)
    clean_data = clean_data.reset_index(drop=True)

    clean_data_compare = pd.read_csv(
        "./tests/samples/sample_weather_data_clean.csv", dtype=object
    )
    pd.testing.assert_frame_equal(clean_data, clean_data_compare)
    print("test")


def test_data_type_conversion() -> None:
    filename = "sample_weather_data_clean.csv"
    meta_col_config = {"__filename": filename}
    data = pd.read_csv(f"./tests/samples/{filename}", dtype=object)
    meta_cols = add_meta_cols(data, meta_col_config)

    compare = pd.read_csv(
        "./tests/samples/sample_weather_data_clean_compare.csv", dtype=object
    )

    pd.testing.assert_frame_equal(meta_cols, compare)


if __name__ == "__main__":
    test_remove_invalid_data()
    test_data_type_conversion()
