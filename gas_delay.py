import pandas as pd
import math
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

def estimate_gas_delay(df, id, work_commute=0, workdays=5, long_car_trip_total_miles = 0, long_trips_per_year = 0, trips_week=0, trip_dist_week=0, trips_weekend=0, trip_dist_weekend=0, previous_convergences=None):
    '''
    Provides an estimate for the annual time in hours spent getting gas.

    Does not provide an estimate for BEVs.
    '''

    car = df[(df['id']==id)]
    for _, row in car.iterrows():
        tech = row['tech']
        mpg_city = row['mpg_city']
        mpg_highway = row['mpg_highway']
        car_class = row['class']

    if tech == "BEV":
        return
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
    weekly_total_fills = math.ceil(((work_commute*2*workdays + trips_week*trip_dist_week*workdays + trip_dist_weekend*trips_weekend*(7-workdays)) * 52) / veh_range - 1)

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

    time_to_fill = 1/6  #assume 10 minutes = 10/60 hours

    gas_delay = total_fills*time_to_fill
    if type(gas_delay) == float:
        gas_delay = round(gas_delay, 1)

    return gas_delay # in hours


# file_path = 'veh.xlsx'
# df = pd.read_excel(file_path)

# id = 48401 #nissan leaf
# work_commute_one_way = 50
# trips_per_day = 2
# longest_trip = 600
# trips_over_threshold = 5
# home_charging = False
# charger_power = 150

# print("Gas:", estimate_gas_delay(df, id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold), "hours")
