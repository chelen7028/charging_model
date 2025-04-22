import pandas as pd
import math
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from gas_delay import estimate_gas_delay

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

def estimate_charging_delay(id, work_commute=0, workdays=5, trips_over_threshold=0, longest_trip=0, home_charger_power=7.2, trips_week=0, trip_dist_week=0, trips_weekend=0, trip_dist_weekend=0, home_charging=False, work_charging=False, previous_convergences=None):
    '''
    Provides an estimate for the annual delay in hours from charging an EV.

    Only works for BEVs and PHEVs.

    A delay is considered time that would otherwise be spent driving/commuting. Overnight charging does not incur any delays.
    '''

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
    
    fast_time_to_charge = battery_capacity/150 # highway fast charging
    home_time_to_charge = battery_capacity/home_charger_power

    
    if work_charging and home_charging: # assume car can be fully charged between every trip and every other on weekends
        workweek_charges = (math.ceil(work_commute / veh_range - 1) * 2 + math.ceil(trip_dist_week / veh_range - 1) * trips_week)*workdays
        weekend_charges = (math.ceil(trip_dist_weekend*2 / veh_range - 1) * trips_weekend)*(7-workdays)

        regular_total_charges = (workweek_charges+weekend_charges)*52
        regular_charging_delay = regular_total_charges * home_time_to_charge

    elif home_charging: # assume car can be fully charged between every other trip
        workweek_charges = (math.ceil(work_commute*2 / veh_range - 1) * 2 + math.ceil(trip_dist_week*2 / veh_range - 1) * trips_week)*workdays
        weekend_charges = (math.ceil(trip_dist_weekend*2 / veh_range - 1) * trips_weekend)*(7-workdays)

        regular_total_charges = (workweek_charges+weekend_charges)*52
        regular_charging_delay = regular_total_charges * home_time_to_charge

    elif work_charging: # assume car can be fully charged at work between every other trip except on weekends which uses fast charging
        workweek_charges = (math.ceil(work_commute*2 / veh_range - 1) * 2 + math.ceil(trip_dist_week*2 / veh_range - 1) * trips_week)*workdays
        weekend_charges = math.ceil(((trip_dist_weekend*trips_weekend)*(7-workdays)) / veh_range - 1)

        regular_charging_delay = workweek_charges*52*home_time_to_charge + weekend_charges*52*fast_time_to_charge
    
    else: # car will charge fully only when needed, using highway fast charging
        regular_total_charges = math.ceil(((work_commute*2*workdays + trips_week*trip_dist_week*workdays + trip_dist_weekend*trips_weekend*(7-workdays)) * 52) / veh_range - 1)
        regular_charging_delay = regular_total_charges*fast_time_to_charge
    

    # long distance trips
    found_match = False

    for _, row in previous_convergences.iterrows():
        row_range = row['range']
        row_longest_trip = row['longest_trip']
        row_trips_over_threshold = row['trips_over_threshold']
        if row_range == veh_range and row_longest_trip == longest_trip and row_trips_over_threshold == trips_over_threshold:
            average_long_charges = round(row['charges'], 1)
            found_match = True
        
    if not found_match:
        elig_trips = fast_charging_distribution(df, id, longest_trip)

        average_long_charges = None
        num_iterations = 0
        epsilon = 0.001

        while True:
            long_trips = select_trips(elig_trips, longest_trip, trips_over_threshold) # array of n=trips_over_threshold trips

            long_trip_charges = 0

            for trip in long_trips:
                long_trip_charges += math.ceil(trip/veh_range - 1)

            if average_long_charges:
                total = average_long_charges*num_iterations+long_trip_charges
                num_iterations += 1
                new_average = total/num_iterations

                if abs(new_average-average_long_charges) <= epsilon:
                    average_long_charges = new_average
                    break
                else:
                    average_long_charges = new_average

            else:
                average_long_charges = long_trip_charges
                num_iterations += 1
        
        new_row = pd.DataFrame([{'range': veh_range,
                                 'longest_trip': longest_trip,
                                 'trips_over_threshold': trips_over_threshold,
                                 'charges': average_long_charges
                                }])
        new_row.to_csv('previous_convergences.csv', mode='a', header=False, index=False)

    long_trip_charging_delay = average_long_charges*fast_time_to_charge

    if type(regular_charging_delay) == float:
        regular_charging_delay = round(regular_charging_delay, 1)
    if type(long_trip_charging_delay) == float:
        long_trip_charging_delay = round(long_trip_charging_delay, 1)

    gas_delay = estimate_gas_delay(df, id, work_commute, workdays, trips_over_threshold, longest_trip, trips_week, trip_dist_week, trips_weekend, trip_dist_weekend, previous_convergences)
    charging_delay = [round(regular_charging_delay/52,1), round(long_trip_charging_delay,1), round(regular_charging_delay+long_trip_charging_delay,1)]
    
    final_delay = charging_delay+gas_delay
    
    return final_delay # in hours

##########################
### Gas Delays ###
##########################

def estimate_gas_delay(df, id, work_commute=0, workdays=5, trips_over_threshold = 0, longest_trip = 0, trips_week=0, trip_dist_week=0, trips_weekend=0, trip_dist_weekend=0, previous_convergences=None):
    '''
    Provides an estimate for the annual time in hours spent getting gas.

    Does not provide an estimate for BEVs.
    '''

    car = df[(df['id']==id)]
    for _, row in car.iterrows():
        mpg_city = 21
        mpg_highway = 27
        car_class = row['class']

    # if tech == "BEV":
    #     return
        #return 'Sorry, battery electric vehicles cannot use gasoline.'
    if ((type(mpg_city) != int and type(mpg_city) != float) or (type(mpg_highway) != int and type(mpg_highway) != float)):
        return 'no mpg data'
        #return 'Sorry, we do not have enough information to estimate the charging delay for this vehicle.'

    tank_size = 16 # gallons
    if car_class == "Compact Car" or car_class == "Two Seater":
        tank_size = 12
    elif car_class == "Compact SUV":
        tank_size = 14
    elif car_class == "Midsize/Large Car":
        tank_size = 14
    elif car_class == "Midsize/Large SUV":
        tank_size = 16
    elif car_class == "Pickup Truck":
        tank_size = 26
    elif car_class == "Minivan/Van":
        tank_size = 20

    avg_mpg = 1/(0.55/mpg_city + 0.45/mpg_highway)
    veh_range = tank_size * avg_mpg
    print(veh_range)

    weekly_total_fills = math.ceil(((work_commute*2*workdays + trips_week*trip_dist_week*workdays + trip_dist_weekend*trips_weekend*(7-workdays)) * 52) / veh_range - 1)

    # long distance trips
    found_match = False

    for _, row in previous_convergences.iterrows():
        row_range = row['range']
        row_longest_trip = row['longest_trip']
        row_trips_over_threshold = row['trips_over_threshold']
        if row_range == veh_range and row_longest_trip == longest_trip and row_trips_over_threshold == trips_over_threshold:
            average_long_fills = round(row['charges'], 1)
            found_match = True
        
    if not found_match:
        elig_trips = fast_charging_distribution(df, id, longest_trip)

        average_long_fills = None
        num_iterations = 0
        epsilon = 0.001

        while True:
            long_trips = select_trips(elig_trips, longest_trip, trips_over_threshold) # array of n=trips_over_threshold trips

            long_trip_charges = 0

            for trip in long_trips:
                long_trip_charges += math.ceil(trip/veh_range - 1)

            if average_long_fills:
                total = average_long_fills*num_iterations+long_trip_charges
                num_iterations += 1
                new_average = total/num_iterations

                if abs(new_average-average_long_fills) <= epsilon:
                    average_long_fills = new_average
                    break
                else:
                    average_long_fills = new_average

            else:
                average_long_fills = long_trip_charges
                num_iterations += 1
        
        new_row = pd.DataFrame([{'range': veh_range,
                                 'longest_trip': longest_trip,
                                 'trips_over_threshold': trips_over_threshold,
                                 'charges': average_long_fills
                                }])
        new_row.to_csv('previous_convergences.csv', mode='a', header=False, index=False)

    long_trip_fills = average_long_fills

    time_to_fill = 1/6  #assume 10 minutes = 10/60 hours

    gas_delay = (weekly_total_fills+long_trip_fills)*time_to_fill

    return [round(weekly_total_fills*time_to_fill/52,1), round(long_trip_fills*time_to_fill,1), round(gas_delay,1)] # in hours

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
        plt.grid(True)
        plt.savefig(f'416_sensitivity_{param}_{str(base_params['home_charging'])}.png')
        

###############
### Testing ###
###############

id = 48401 # Nissan Leaf 2025 (range 212)
work_commute_one_way = 10
workdays = 5
longest_trip = 600
trips_over_threshold = 5
home_charging = True
work_charging = True
charger_power = 7.2
trips_week=2
trip_dist_week=10
trips_weekend=2
trip_dist_weekend=10

previous_convergences = pd.read_csv('previous_convergences.csv')

print("Gas:", estimate_gas_delay(df, id, work_commute_one_way, workdays, trips_over_threshold, longest_trip, trips_week, trip_dist_week, trips_weekend, trip_dist_weekend, previous_convergences=previous_convergences), "hours")


###### Delay Output ######
# print("EV:", estimate_charging_delay(id, work_commute_one_way, workdays, longest_trip, trips_over_threshold, charger_power, trips_week, trip_dist_week, trips_weekend, trip_dist_weekend, home_charging, work_charging, previous_convergences), "hours")

###### Convergence Graph Generation ######
# convergence_graphs(id, [600, 800, 1200], [3,5,8])

###### Sensitivity Analysis ######
param_ranges = {
    # 'work_commute': [10, 100],           # in miles
    # 'trips_per_day': [1, 10],
    'longest_trip': [250, 1200],           # in miles
    # 'trips_over_threshold': [1, 30],
}

base_params = {
    'id': 48401,
    'work_commute': 20,
    'trips_per_day': 2,
    'longest_trip': 300,
    'trips_over_threshold': 5,
    'home_charging': True,
    'previous_convergences': previous_convergences,
}

# sensitivity_analysis(param_ranges, base_params)

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
