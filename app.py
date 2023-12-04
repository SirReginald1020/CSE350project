import csv
from flask import Flask, render_template
import pandas as pd
import os
import shutil
from kaggle.api.kaggle_api_extended import KaggleApi
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly
import plotly.express as px
import json

app = Flask(__name__)

from flask import render_template
from flask_mail import Mail, Message

mail = Mail(app)

@app.errorhandler(500)
def internal_error(error):
    # Send an email to your support email with the error details
    msg = Message('Internal Server Error', sender='cmcarp05@louisville.edu', recipients=['ccarpenter0527@gmail.com'])
    msg.body = str(error)
    mail.send(msg)
    return render_template('500.html'), 500

from flask import Response


@app.route('/download-data')
def download_data():
    fuel_data = get_csv_from_kaggle()
    if fuel_data is not None:
        csv = fuel_data.to_csv(index=False)  # Convert DataFrame to CSV string
        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=fuel_data.csv"}
        )
    else:
        return "Error: No data found!", 404

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

from flask import request

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get the search query and filter criteria from the form
    search_query = request.form.get('search_query')
    filter_fuel_type1 = request.form.get('filter_fuel_type1')
    filter_fuel_type2 = request.form.get('filter_fuel_type2')

    # Get the data
    fuel_data = get_csv_from_kaggle()

    # If the data is successfully retrieved, convert it to records for display
    if fuel_data is not None:
        if search_query:
            # Filter data based on the search query (modify this logic as needed)
            fuel_data = fuel_data[fuel_data['Make'].str.contains(search_query, case=False) |
                                  fuel_data['Model'].str.contains(search_query, case=False)]
        
        if filter_fuel_type1:
            # Filter data by Fuel Type 1
            fuel_data = fuel_data[fuel_data['Fuel Type 1'] == filter_fuel_type1]

        if filter_fuel_type2:
            # Filter data by Fuel Type 2
            fuel_data = fuel_data[fuel_data['Fuel Type 2'] == filter_fuel_type2]

        data_records = fuel_data.to_dict(orient='records')
        return render_template('index.html', data=data_records, search_query=search_query)
    else:
        return render_template('error.html', message="Data could not be loaded.")

@app.route('/page1')
def page1():
    # Get the data
    fuel_data = get_csv_from_kaggle()

    # If the data is successfully retrieved, convert it to records for display
    if fuel_data is not None:
        data_records = fuel_data.to_dict(orient='records')

        # Create the chart
        plt.figure(figsize=(8, 4))
        sorted_data = fuel_data.groupby('Fuel Type 1')['Annual Fuel Cost (FT1)'].mean().sort_values(ascending=False)
        sorted_data.plot(kind='bar', color='skyblue')
        plt.title('Average Annual Fuel Cost (FT1) by Fuel Type 1')
        plt.xlabel('Fuel Type 1', fontsize=11, fontweight='bold', labelpad=20)  # Set font size, make it bold, and adjust label position
        plt.ylabel('Average Annual Fuel Cost', fontsize=11, fontweight='bold')  # Adjust label position for the y-axis
        plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for better readability
        plt.tight_layout()

        # Save the plot to a BytesIO object
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)

        # Convert the image to base64 for embedding in HTML
        img_str = base64.b64encode(img.read()).decode('utf-8')

        # Pass the data and image to the template
        return render_template('page1.html', data_records=data_records, img_str=img_str)
    else:
        return render_template('error.html', message="Data could not be loaded.")


@app.route('/page2')
def page2():
    # Get the data
    fuel_data = get_csv_from_kaggle()

    # If the data is successfully retrieved, convert it to records for display
    if fuel_data is not None:
        # Create the chart for Fuel Type 2
        plt.figure(figsize=(8, 4))
        sorted_data_page2 = fuel_data.groupby('Fuel Type 2')['Annual Fuel Cost (FT2)'].mean().sort_values(ascending=False)
        sorted_data_page2.plot(kind='bar', color='lightcoral')
        plt.title('Average Annual Fuel Cost (FT2) by Fuel Type 2')
        plt.xlabel('Fuel Type 2', fontsize=11, fontweight='bold', labelpad=20)
        plt.ylabel('Average Annual Fuel Cost', fontsize=11, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save the plot to a BytesIO object
        img_page2 = BytesIO()
        plt.savefig(img_page2, format='png')
        img_page2.seek(0)

        # Convert the image to base64 for embedding in HTML
        img_str_page2 = base64.b64encode(img_page2.read()).decode('utf-8')

        # Pass the image to the template
        return render_template('page2.html', img_str_page2=img_str_page2)
    else:
        return render_template('error.html', message="Data could not be loaded.")


@app.route('/page3')
def page3():
    # Get the data
    fuel_data = get_csv_from_kaggle()

    # If the data is successfully retrieved, convert it to records for display
    if fuel_data is not None:
        # Group by 'Make' and calculate the average annual fuel cost (FT1)
        make_avg_fuel_cost = fuel_data.groupby('Make')['Annual Fuel Cost (FT1)'].mean()

        # Select the top 5 makes with the lowest average annual fuel cost
        top_5_low_cost_makes = make_avg_fuel_cost.nsmallest(5)

        # Create bar chart for top 5 makes with lowest average annual fuel cost
        plt.figure(figsize=(10, 6))  # Increased figure size

        # Top 5 makes with lowest average annual fuel cost
        plt.bar(top_5_low_cost_makes.index, top_5_low_cost_makes, color='lightblue')
        plt.title('Top 5 Makes with Lowest Average Annual Fuel Cost (FT1)')
        plt.xlabel('Make', fontsize=12, fontweight='bold', labelpad=20)
        plt.ylabel('Average Annual Fuel Cost', fontsize=12, fontweight='bold')
        plt.xticks(range(len(top_5_low_cost_makes)), top_5_low_cost_makes.index, rotation=45, ha='right')

        plt.tight_layout(pad=4.0, h_pad=None, w_pad=None, rect=[0, 0.1, 1, 1])
        plt.subplots_adjust(bottom=0.15)  # Adjust bottom spacing

        # Save the plot to a BytesIO object
        img_low_cost = BytesIO()
        plt.savefig(img_low_cost, format='png', bbox_inches='tight')
        img_low_cost.seek(0)

        # Convert the image to base64 for embedding in HTML
        img_str_low_cost = base64.b64encode(img_low_cost.read()).decode('utf-8')

        # Close the current figure to release resources
        plt.close()

        # Pass the data and image to the template
        return render_template('page3.html', img_str_low_cost=img_str_low_cost)
    else:
        return render_template('error.html', message="Data could not be loaded.")

@app.route('/page4')
def page4():
    # Get the data
    fuel_data = get_csv_from_kaggle()

    if fuel_data is not None:
        # Filter out rows where 'Annual Fuel Cost (FT2)' is 0
        filtered_data = fuel_data[fuel_data['Annual Fuel Cost (FT2)'] > 0]

        # Now group by 'Make' and calculate the average annual fuel cost (FT2)
        make_avg_fuel_cost_ft2 = filtered_data.groupby('Make')['Annual Fuel Cost (FT2)'].mean()

        # Select the top 5 makes with the lowest average annual fuel cost for Fuel Type 2
        top_5_low_cost_makes_ft2 = make_avg_fuel_cost_ft2.nsmallest(5)

        # Create a Plotly bar chart
        fig = px.bar(top_5_low_cost_makes_ft2, x=top_5_low_cost_makes_ft2.index, y=top_5_low_cost_makes_ft2,
                     labels={'x': 'Make', 'y': 'Average Annual Fuel Cost (FT2)'},
                     title='Top 5 Makes with Lowest Average Annual Fuel Cost (FT2)')

        # Convert the figure to JSON
        plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        # Pass the plotly figure JSON to the template
        return render_template('page4.html', plot_json=plot_json)

    else:
        return render_template('error.html', message="Data could not be loaded.")
@app.route('/page5')
def page5():
    return render_template('page5.html')
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
