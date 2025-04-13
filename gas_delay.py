import pandas as pd
import math
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

def estimate_gas_delay(df, id, work_commute=0, trips_per_day=0, long_car_trip_total_miles = 0, long_trips_per_year = 0):
    '''
    Provides an estimate for the annual time in hours spent getting gas.

    Does not provide an estimate for BEVs.
    '''
    days = 260

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
    daily_mileage = (work_commute * trips_per_day * days) // veh_range / days

    total_fills = (daily_mileage*days) + (long_car_trip_total_miles//veh_range*long_trips_per_year)
    time_to_fill = 1/6  #assume 10 minutes = 10/60 hours

    gas_delay = total_fills*time_to_fill
    if type(gas_delay) == float:
        gas_delay = round(gas_delay, 1)

    return gas_delay # in hours


file_path = 'veh.xlsx'
df = pd.read_excel(file_path)

id = 48401 #nissan leaf
work_commute_one_way = 50
trips_per_day = 2
longest_trip = 600
trips_over_threshold = 5
home_charging = False
charger_power = 150

print("Gas:", estimate_gas_delay(df, id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold), "hours")
