import pandas as pd
import math
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

file_path = 'veh.xlsx'
df = pd.read_excel(file_path)

def fast_charging_distribution(df, id, longest_trip):
    trip_data_path = 'tripv2pub.xlsx'
    trip_df = pd.read_excel(trip_data_path)

    car = df[(df['id']==id)]
    for _, row in car.iterrows():
        veh_range = row['range']

    eligible_trips = []

    for i, row in trip_df.iterrows():
        dist = row["TRPMILES"]
        if dist <= longest_trip and dist >= veh_range:
            eligible_trips.append(float(dist))
    
    return eligible_trips

def select_trips(eligible_trips, longest_trip, trips_over_threshold):
    # select trips
    long_trips = [longest_trip]
    for _ in range(trips_over_threshold-1):
        long_trips.append(float(random.choice(eligible_trips)))

    return long_trips

# fast_charging_distribution(df, 47492, 1000, 10)

def estimate_charging_delay(id, work_commute=0, trips_per_day=0, longest_trip = 0, trips_over_threshold = 0, home_charging=True, charger_power=150, previous_convergences=None):
    '''
    Provides an estimate for the annual delay in hours from charging an EV.

    Only works for BEVs and PHEVs.

    A delay is considered time that would otherwise be spent driving/commuting. Overnight charging does not incur any delays.
    '''
    days = 260

    df = pd.read_excel('veh.xlsx')

    car = df[(df['id']==id)]
    for _, row in car.iterrows():
        tech = row['tech']
        veh_range = row['range']
        battery_capacity = row['battery_capacity_kwh']

    if tech != "BEV" and tech != "PHEV":
        return 'Not a chargeable vehicle.'
    if type(veh_range) != int and type(veh_range) != float:
        return 'Not enough information.'
    if trips_per_day == 0 and trips_over_threshold == 0:
        return 0

    number_of_charges_per_day = 0

    if home_charging: # assume car can be fully charged between every other trip
        if work_commute*2 <= veh_range:
          number_of_charges_per_day = 0
        else:
          number_of_charges_per_day = math.ceil(work_commute*2 / veh_range - 1) * trips_per_day
        total_charges = number_of_charges_per_day*days

    else: # car will charge fully only when needed
        total_charges = math.ceil((work_commute * trips_per_day * days) / veh_range - 1)
    

    found_match = False

    for _, row in previous_convergences.iterrows():
        row_range = row['range']
        row_longest_trip = row['longest_trip']
        row_trips_over_threshold = row['trips_over_threshold']
        if row_range == veh_range and row_longest_trip == longest_trip and row_trips_over_threshold == trips_over_threshold:
            average_charges = row['charges']
            found_match = True
        
    if not found_match:
        elig_trips = fast_charging_distribution(df, id, longest_trip)

        average_charges = None
        num_iterations = 0
        epsilon = 0.001

        while True:
            long_trips = select_trips(elig_trips, longest_trip, trips_over_threshold) # array of n=trips_over_threshold trips

            long_trip_charges = 0

            for trip in long_trips:
                long_trip_charges += math.ceil(trip/veh_range - 1)

            if average_charges:
                total = average_charges*num_iterations+long_trip_charges
                num_iterations += 1
                new_average = total/num_iterations

                if abs(new_average-average_charges) <= epsilon:
                    average_charges = new_average
                    break
                else:
                    average_charges = new_average

            else:
                average_charges = long_trip_charges
                num_iterations += 1
        
        new_row = pd.DataFrame([{'range': veh_range,
                                 'longest_trip': longest_trip,
                                 'trips_over_threshold': trips_over_threshold,
                                 'charges': average_charges
                                }])
        new_row.to_csv('previous_convergences.csv', mode='a', header=False, index=False)
        
    total_charges += average_charges
    time_to_charge = (battery_capacity/charger_power)

    charging_delay = total_charges*time_to_charge
    if type(charging_delay) == float:
        charging_delay = round(charging_delay, 1)

    return charging_delay # in hours

##########################
### Convergence Graphs ###
##########################

def convergence_graphs(id, longest_trip, trips_over_threshold):
    fig, ax = plt.subplots(nrows=len(longest_trip), ncols=len(trips_over_threshold), figsize=(10.0, 10.0))
    df = pd.read_excel('veh.xlsx')

    for i in range(len(longest_trip)):
        for j in range(len(trips_over_threshold)):

            car = df[(df['id']==id)]
            for _, row in car.iterrows():
                tech = row['tech']
                veh_range = row['range']

            if tech != "BEV" and tech != "PHEV":
                return
            if type(veh_range) != int and type(veh_range) != float:
                return 'no range'

            average_charges = None
            num_iterations = 0
            epsilon = 0.001
            all_averages = []

            elig_trips = fast_charging_distribution(df, id, longest_trip[i])

            while True:
                long_trips = select_trips(elig_trips, longest_trip[i], trips_over_threshold[j]) # array of n=trips_over_threshold trips

                long_trip_charges = 0

                for trip in long_trips:
                    long_trip_charges += math.ceil(trip/veh_range - 1)

                if average_charges:
                    total = average_charges*num_iterations+long_trip_charges
                    num_iterations += 1
                    new_average = total/num_iterations
                    all_averages.append(new_average)

                    if abs(new_average-average_charges) <= epsilon:
                        average_charges = new_average
                        break

                    else:
                        average_charges = new_average

                else:
                    average_charges = long_trip_charges
                    num_iterations += 1
                
                all_averages.append(average_charges)
            
            ax[i,j].plot(range(1,len(all_averages)+1), all_averages, marker='.', linestyle='-')
            ax[i,j].set_title(f'Longest trips: {str(longest_trip[i])}, Total long trips: {str(trips_over_threshold[j])}', fontsize=7)
            # ax[i,j].grid(True)

    # Add labels and title
    fig.supxlabel("Iteration")
    fig.supylabel("Number of Charges (Running Average)")
    fig.suptitle("Convergence of Long-Distance Trip Charging Delay Estimate (epsilon=0.001)")
    fig.tight_layout()
    fig.savefig('convergence_graph.png')
    
    return

############################
### Sensitivity Analysis ###
############################

def sensitivity_analysis(param_ranges, base_params):
    results = {}

    for param in param_ranges:
        if param == 'work_commute':
            values = np.linspace(param_ranges[param][0], param_ranges[param][1], num=20, dtype=int, endpoint=False)
        elif param == 'longest_trip':
            values = np.linspace(param_ranges[param][0], param_ranges[param][1], num=20, dtype=int, endpoint=False)
        elif param == 'trips_per_day': # trips per day or per year
            values = np.linspace(param_ranges[param][0], param_ranges[param][1], num=10, dtype=int, endpoint=False)
        else:
            values = np.linspace(param_ranges[param][0], param_ranges[param][1], num=20, dtype=int, endpoint=False)


        delays = []
        for val in values:
            params = base_params.copy()
            params[param] = val
            delay = estimate_charging_delay(**params)
            delays.append(delay)

        results[param] = (values, delays)

    for param, (x, y) in results.items():
        plt.figure()
        plt.plot(x, y, marker='o')
        if base_params['home_charging'] == False:
            plt.title(f"Sensitivity of charging delay estimate to {param} with no home charging", fontsize=10)
        else:
            plt.title(f"Sensitivity of charging delay estimate to {param} with home charging", fontsize=10)
        plt.xlabel(param)
        plt.ylabel("Charging Delay (hours)")
        plt.savefig(f'aggregate_sensitivity_{param}_{str(base_params['home_charging'])}.png')

###############
### Testing ###
###############

id = 48401 # Nissan Leaf 2025 (range 212)
work_commute_one_way = 50
trips_per_day = 2
longest_trip = 600
trips_over_threshold = 5
home_charging = False
charger_power = 150

previous_convergences = pd.read_csv('previous_convergences.csv')

###### Delay Output ######
# print("EV:", estimate_charging_delay(id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold, home_charging, charger_power, previous_convergences), "hours")

###### Convergence Graph Generation ######
# convergence_graphs(id, [600, 800, 1200], [3,5,8])

###### Sensitivity Analysis ######
param_ranges = {
    'work_commute': [10, 100],           # in miles
    'trips_per_day': [1, 10],
    'longest_trip': [300, 1200],           # in miles
    'trips_over_threshold': [1, 30],
}

base_params = {
    'id': 48401,
    'work_commute': 20,
    'trips_per_day': 2,
    'longest_trip': 300,
    'trips_over_threshold': 5,
    'home_charging': False,
    'previous_convergences': previous_convergences,
}

sensitivity_analysis(param_ranges, base_params)

####################
### Write to CSV ###
####################

# charging_delays = []
# for _, row in df.iterrows():
#   id = row['id']

#   charging_delay = estimate_charging_delay(df, id, work_commute, trips_per_day, longest_trip_over_year, long_trips_above_threshold_dist_or_time_per_year, home_charging, work_charging)
#   charging_delays.append(charging_delay)

# df['annual_delay_hours'] = charging_delays

# df.to_csv('/Users/helenchen/Desktop/Thesis/charging_delay.csv', index=False, mode='w+')  # Replace with your desired output path
