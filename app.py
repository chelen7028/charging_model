# app.py

from flask import Flask, render_template, request
from charging_delay import estimate_charging_delay  # Import your function

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get input values from the form
        inputs = [
            int(request.form['id']),
            int(request.form['commute']),
            int(request.form['numCommutes']),
            int(request.form['longestTrip']),
            int(request.form['numOverRange']),
        ]
        
        # Get make and model (optional)
        # make = request.form['make']
        # model = request.form['model']
        home_charging = request.form['home_charging']

        # Calculate the result using the imported function
        home_charging_bool = True if home_charging == "yes" else False
        result = estimate_charging_delay(*inputs,home_charging=home_charging_bool)
        
        return render_template('index.html', result=result)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)
