import csv
from flask import Flask, render_template
import pandas as pd
import os
import shutil
from kaggle.api.kaggle_api_extended import KaggleApi
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

# ... rest of your Flask app code ...

@app.route('/download-data')
def download_data():
    fuel_data = get_csv_from_kaggle()  # Make sure this is the same function you use to get the DataFrame
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

    writehtml = False
    if writehtml:
        # To make the graph use avg_prices_peryear.csv
        fpath = 'dataset-folder/avg_prices_peryear.csv'
        years = []
        cost_1 = []
        cost_2 = []

        with open(fpath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                years.append(row['Year'])
                cost_1.append(row['Annual Fuel Cost (FT1)'])
                cost_2.append(row['Annual Fuel Cost (FT2)'])
        chart_data = "['Year', 'Annual Cost (FT1)', 'Annual Cost (FT2)'],\n"
        for i in range(len(years)):
            chart_data += f"['{years[i]}', {cost_1[i]}, {cost_2[i]}], \n"
        existing_html = 'templates/page1.html'
        with open(existing_html, 'r') as existing:
            html_content = existing.read()

        placeholder = '<!-- placeholder for chart -->'
        chartscript = f'''
        google.charts.load('current', {{"packages":["corechart"]}}); 
    
        google.charts.setOnLoadCallback(drawChart); 
    
        function drawChart() {{ 
    
            var data = google.visualization.arrayToDataTable([ 
    
                {chart_data} 
    
            ]); 
    
            var options = {{ 
    
                title: 'Average of Annual Fuel Costs Over Years', 
    
                curveType: 'function', 
    
                legend: {{ position: 'bottom' }} 
    
            }}; 
    
            var chart = new google.visualization.LineChart(document.getElementById('curve_chart')); 
    
            chart.draw(data, options); 
        }} '''
        html_content = html_content.replace(placeholder, chartscript)
        with open(existing_html, 'w') as existing:
            existing.write(html_content)


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
        plt.xlabel('Fuel Type 1')
        plt.ylabel('Average Annual Fuel Cost (FT1)')
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
