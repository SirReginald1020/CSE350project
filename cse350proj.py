import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import kaggle
import os


# helper function
# connect to kaggle using D's api token
def connect_to_kaggle():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()


# function that takes in the url, determines if it's .csv or .xlsx and gets the data
def get_csv_from_kaggle():
    # establish and authenticate connection
    connect_to_kaggle()
    # identify current directory, send name of dataset, make folder, unpack dataset
    current_directory = os.getcwd()
    dataset_name = "epa/fuel-economy"
    savepath = os.path.join(current_directory, 'dataset-folder')
    kaggle.api.dataset_download_files(dataset_name, path=savepath, unzip=True)
    # read and make usable the data
    filepath = 'dataset-folder/database.csv'
    data = pd.read_csv(filepath)
    return data


def simple_display(table):
    print("Data table: \n")
    print(table)


if __name__ == '__main__':
    # I know this doesn't look like much but this was 5 hours of work with much trial and error.
    # get the csv and make a table out of it
    fuel_data = get_csv_from_kaggle()
    simple_display(fuel_data)

