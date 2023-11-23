import csv
from flask import Flask, render_template
import pandas as pd
import os
import shutil
from kaggle.api.kaggle_api_extended import KaggleApi


app = Flask(__name__)


# Function to find and organize any HTML files in the project directory
def html_into_templates(proj_path, debug):

    t_folder = os.path.join(proj_path, "templates")
    if not os.path.exists(t_folder):
        os.makedirs(t_folder)
        if debug:
            print("Didn't find a \'templates\' folder, making one now!")
    else:
        if debug:
            print("Found the templates folder!")

    # Find all the html files not yet in templates
    htmlist = [f for f in os.listdir(proj_path) if f.endswith('.html')]

    for h_file in htmlist:
        startpoint = os.path.join(proj_path, h_file)
        destination = os.path.join(t_folder, h_file)

        # check to see if the file is already in templates, move it there if not.
        if startpoint != destination:
            shutil.move(startpoint, destination)
            if debug:
                print("Moved", h_file, "to", t_folder)


# Function tailored to our csv, will remove columns.
def cut_csv(filein, fileout, colstokeep):
    # Rename the file, so we don't have to change handling elsewhere
    if not os.path.exists("dataset-folder/init.csv"):
        try:
            oldpath = os.path.join("dataset-folder", "database.csv")
            newpath = os.path.join("dataset-folder", "init.csv")
            os.rename(oldpath, newpath)
            filein = "init.csv"
        except FileNotFoundError:
            print("Couldn't find", filein)

    with open('dataset-folder/init.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames

        colstodel = [col for col in fieldnames if col not in colstokeep]
        with open('dataset-folder/database.csv', 'w', newline='') as fileout:
            writer = csv.DictWriter(fileout, fieldnames=[col for col in fieldnames if col not in colstodel])
            writer.writeheader()

            for row in reader:
                for col in colstodel:
                    del row[col]
                writer.writerow(row)


# Function that sets up the Kaggle API connection and authenticates
def connect_to_kaggle():
    api = KaggleApi()
    api.authenticate()
    return api


# Function that downloads dataset from Kaggle and returns a Pandas DataFrame
def get_csv_from_kaggle():
    # Establish and authenticate connection
    api = connect_to_kaggle()

    # Define the current directory and dataset path
    current_directory = os.getcwd()
    dataset_name = "epa/fuel-economy"
    if not os.path.exists('dataset-folder'):
        os.makedirs('dataset-folder')
    savepath = os.path.join(current_directory, 'dataset-folder')

    # Create the dataset folder if it doesn't exist
    if not os.path.exists(savepath):
        os.makedirs(savepath)

    # Download dataset files
    api.dataset_download_files(dataset_name, path=savepath, unzip=True)

    # Assuming the file is named 'database.csv' and is located in the folder 'dataset-folder'
    filepath = os.path.join(savepath, 'database.csv')

    # Check if the file exists before reading
    if os.path.exists(filepath):
        # Limit the data, keep is what we keep
        keep = ['Year', 'Make', 'Model', 'Fuel Type 1', 'Fuel Type 2', 'Annual Fuel Cost (FT1)',
                'Annual Fuel Cost (FT2)']
        cut_csv('database.csv', 'database.csv', keep)
        data = pd.read_csv(filepath)
        return data
    else:
        print(f"File {filepath} not found. Check if the dataset contains 'database.csv'.")
        return None


@app.route('/')
def index():
    # Get the data
    fuel_data = get_csv_from_kaggle()

    # If the data is successfully retrieved, convert it to records for display
    if fuel_data is not None:
        data_records = fuel_data.to_dict(orient='records')
        return render_template('/index.html', data=data_records)
    else:
        return render_template('error.html', message="Data could not be loaded.")


if __name__ == '__main__':
    # Debugging?
    debug: bool = True

    # kaggle stuff
    connect_to_kaggle()
    get_csv_from_kaggle()

    # Organize html(s)
    html_into_templates(os.getcwd(), debug)

    # Run app
    if debug:
        app.run(debug=True)
    if not debug:
        app.run()

