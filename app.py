# app.py

from flask import Flask, render_template, request
from charging_delay import estimate_charging_delay
from gas_delay import estimate_gas_delay
import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get input values from the form

        home_charging = request.form['home_charging']
        work_charging = request.form['work_charging']

        # Calculate the result using the imported function
        home_charging_bool = True if home_charging == "yes" else False
        work_charging_bool = True if work_charging == "yes" else False

        if not request.form['home_charger_power']:
            power = 7.2
        else:
            power = float(request.form['home_charger_power'])

        charging_inputs = [
            int(request.form['id']),
            int(request.form['commute']),
            int(request.form['numCommutes']),
            int(request.form['numOverRange']),
            int(request.form['longestTrip']),
            power,
            int(request.form['trip_week']),
            int(request.form['trip_dist_week']),
            int(request.form['trip_weekend']),
            int(request.form['trip_dist_weekend']),
            home_charging_bool,
            work_charging_bool,
        ]

        result = estimate_charging_delay(*charging_inputs,previous_convergences=pd.read_csv('previous_convergences.csv'))
        
        return render_template('index.html', result=result)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)
