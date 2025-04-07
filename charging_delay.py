import pandas as pd
import math
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


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

def estimate_charging_delay(df, id, work_commute=0, trips_per_day=0, longest_trip = 0, trips_over_threshold = 0, home_charging=True, charger_power=150, plot_convergence = False):
    '''
    Provides an estimate for the annual delay in hours from charging an EV.

    Only works for BEVs and PHEVs.

    A delay is considered time that would otherwise be spent driving/commuting. Overnight charging does not incur any delays.
    '''
    days = 260

    car = df[(df['id']==id)]
    for _, row in car.iterrows():
        tech = row['tech']
        veh_range = row['range']
        battery_capacity = row['battery_capacity_kwh']

    if tech != "BEV" and tech != "PHEV":
        return
        #return 'Sorry, we only support battery electric and plug-in hybrid vehicles.'
    if type(veh_range) != int and type(veh_range) != float:
        return 'no range'
        #return 'Sorry, we do not have enough information to estimate the charging delay for this vehicle.'
    if trips_per_day == 0 and trips_over_threshold == 0:
        return 0

    number_of_charges_per_day = 0

    # if home_charging and work_charging: # assume car can be fully charged between every trip
    #     if work_commute <= veh_range:
    #       number_of_charges_per_day = 0
    #     else:
    #       number_of_charges_per_day = math.ceil(work_commute / veh_range - 1) * trips_per_day
    #     total_charges = number_of_charges_per_day*days

    if home_charging: # assume car can be fully charged between every other trip
        if work_commute*2 <= veh_range:
          number_of_charges_per_day = 0
        else:
          number_of_charges_per_day = math.ceil(work_commute*2 / veh_range - 1) * trips_per_day
        total_charges = number_of_charges_per_day*days

    else: # car will charge fully only when needed
        total_charges = math.ceil((work_commute * trips_per_day * days) / veh_range - 1)

    elig_trips = fast_charging_distribution(df, id, longest_trip)

    average_charges = None
    num_iterations = 0
    epsilon = 0.005
    all_averages = []

    while True:
        long_trips = select_trips(elig_trips, longest_trip, trips_over_threshold) # array of n=trips_over_threshold trips

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
    
    if plot_convergence:
        _, ax = plt.subplots()
        ax.plot(range(1,len(all_averages)+1), all_averages, marker='.', linestyle='-')

        # Add labels and title
        plt.xlabel("Iteration")
        plt.ylabel("Number of Charges (Running Average)")
        plt.title("Average estimated number of charges from NHTS Dataset for long-distance trips")
        plt.show()

    #print('final long charges', long_trip_charges) 
    total_charges += long_trip_charges
    time_to_charge = (battery_capacity/charger_power)

    charging_delay = total_charges*time_to_charge
    if type(charging_delay) == float:
        charging_delay = round(charging_delay, 1)

    return charging_delay # in hours

###############
### Testing ###
###############

id = 48401 #nissan leaf
work_commute_one_way = 50
trips_per_day = 2
longest_trip = 600
trips_over_threshold = 5
home_charging = False
charger_power = 150

print("EV:", estimate_charging_delay(df, id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold, home_charging, charger_power, True), "hours")


# id = 47908 #Tesla model 3
# work_commute_one_way = 50
# trips_per_day = 2
# longest_trip = 600
# trips_over_threshold = 3
# home_charging = False
# charger_power = 150

# print("EV:", estimate_charging_delay(df, id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold, home_charging, charger_power, True), "hours")

#################
### Gas Delay ###
#################

# def estimate_gas_delay(df, id, work_commute=0, trips_per_day=0, long_car_trip_total_miles = 0, long_trips_per_year = 0):
    # '''
    # Provides an estimate for the annual time in hours spent getting gas.

    # Does not provide an estimate for BEVs.
    # '''
    # days = 260

    # car = df[(df['id']==id)]
    # for _, row in car.iterrows():
    #     tech = row['tech']
    #     mpg_city = row['mpg_city']
    #     mpg_highway = row['mpg_highway']
    #     car_class = row['class']

    # if tech == "BEV":
    #     return
    #     #return 'Sorry, battery electric vehicles cannot use gasoline.'
    # if ((type(mpg_city) != int and type(mpg_city) != float) or (type(mpg_highway) != int and type(mpg_highway) != float)):
    #     return 'no mpg data'
    #     #return 'Sorry, we do not have enough information to estimate the charging delay for this vehicle.'

    # tank_size = 16 # gallons
    # if car_class == "Compact Car" or car_class == "Two Seater":
    #     tank_size = 12
    # elif car_class == "Compact SUV":
    #     tank_size = 14
    # elif car_class == "Midsize/Large Car":
    #     tank_size = 14
    # elif car_class == "Midsize/Large SUV":
    #     tank_size = 16
    # elif car_class == "Pickup Truck":
    #     tank_size = 26
    # elif car_class == "Minivan/Van":
    #     tank_size = 20

    # avg_mpg = 1/(0.55/mpg_city + 0.45/mpg_highway)
    # veh_range = tank_size * avg_mpg
    # daily_mileage = (work_commute * trips_per_day * days) // veh_range / days

    # total_fills = (daily_mileage*days) + (long_car_trip_total_miles//veh_range*long_trips_per_year)
    # time_to_fill = 1/6  #assume 10 minutes = 10/60 hours

    # gas_delay = total_fills*time_to_fill
    # if type(gas_delay) == float:
    #     gas_delay = round(gas_delay, 1)

    # return gas_delay # in hours

# print("Gas:", estimate_gas_delay(df, id, work_commute_one_way, trips_per_day, longest_trip, trips_over_threshold), "hours")

# charging_delays = []
# gas_delays = []
# for _, row in df.iterrows():
#   id = row['id']

#   charging_delay = estimate_charging_delay(df, id, work_commute, trips_per_day, longest_trip_over_year, long_trips_above_threshold_dist_or_time_per_year, home_charging, work_charging)
#   charging_delays.append(charging_delay)

#   gas_delay = estimate_gas_delay(df, id, work_commute, trips_per_day, longest_trip_over_year, long_trips_above_threshold_dist_or_time_per_year)
#   gas_delays.append(gas_delay)

# df['annual_delay_hours'] = charging_delays
# df['annual_gas_delay_hours'] = gas_delays

# df.to_csv('/Users/helenchen/Desktop/Thesis/charging_delay.csv', index=False, mode='w+')  # Replace with your desired output path
