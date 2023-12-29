import os
import csv
import math
import numpy as np
import pandas as pd
import json


class wind:
    def __init__(self, hub_height=80, rated_power=1790, cutin_speed=3, cutout_speed=23, temperature_lapse_rate = 0.0065,
                 gravity = 9.8,gas_constant = 8.314, molar_mass_air = 0.0289644, capacity=1790,wakeloss= 0,lifetime=25,
                 inflation_rate=0.025,capex_per_kw = 1501 ,opex = 40,
                 file_name ="/Users/fengxiaotong/Desktop/sedat_model_selection-main/wind_speed/output_(-74.899796 43.104893).csv",
                 new_folder_path='/tmp/results'):
        # input
        self.hub_height = hub_height
        self.rated_power = rated_power
        self.cutin_speed = cutin_speed
        self.cutout_speed = cutout_speed
        self.temperature_lapse_rate=temperature_lapse_rate
        self.gravity= gravity
        self.gas_constant=gas_constant
        self.molar_mass_air=molar_mass_air
        self.capacity= capacity # MWh per year --> MW
        self.wakeloss = float(wakeloss) # In percentage or decimal
        self.lifetime = lifetime
        self.inflation_rate = inflation_rate
        self.capex_per_kw = capex_per_kw
        self.opex = opex   #$/kw
        self.file_name = file_name
        self.new_folder_path= new_folder_path

        # Initialize wind_output as an empty dictionary
        self.wind_output = {}

    # output
    # output value
    # performance parameters

    def windpower(self):
        # Initialize variables with default values
        Adjust_power_air_density = None
        P_Pr_air_density = None
        P_Pr = None
        if not os.path.exists(self.new_folder_path):
            os.makedirs(self.new_folder_path)
        # file_list = os.listdir(self.file_name)
        # for file_name in file_list:
        if self.file_name.endswith('.csv') and os.path.exists(self.file_name):
                # check if the file exists
                _, file_name_only = os.path.split(self.file_name)
                new_file_path = os.path.join(self.new_folder_path, f"new_{file_name_only}")
                # construct the new file path
                # Open the original CSV file and the new file
                with open(self.file_name, 'r') as file, open(new_file_path, 'w', newline='') as new_file:
                    reader = csv.reader(file)
                    writer = csv.writer(new_file)

                    rows = list(reader)  # read all rows

                    # Append data at the end of the first row
                    rows[1].extend(
                        ['alpha', 'estimated speed at hub height (m/s)', "hub temperature (K)", "hub pressure (Pa)",
                         "hub air density",
                         'Power(MW)', "Adjust power based on air pressure (MW)", 'P/Pr', "P/Pr(air density)",
                         'Rated Power', '2MW', 'Cut-in speed', 'm/s', 'Cut-out speed', 'm/s'])

                    # create new file
                    writer.writerows(rows)

                # Read the new file and apply the formulas to the corresponding rows in columns
                df = pd.read_csv(new_file_path, header=1)
                # estimate speed
                if self.hub_height != 80:
                    df["alpha"] = (df['wind speed at 80m (m/s)'] / df['wind speed at 100m (m/s)']). \
                        apply(lambda x: math.log(x) / math.log(80 / 100))
                    df["estimated speed at hub height (m/s)"] = df['wind speed at 80m (m/s)'] * (
                                self.hub_height / 80) ** df[
                                                                    "alpha"]
                else:
                    df["estimated speed at hub height (m/s)"] = df['wind speed at 80m (m/s)']

                # Calculate the average of "estimated speed at hub height (m/s)"
                average_speed = df["estimated speed at hub height (m/s)"].mean()
                # Perform different curve calculations based on the average wind speed
                if average_speed < 8.5:
                    # Prepare data and probabilities
                    data = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22])
                    probabilities = np.array(
                        [0, 0, 0, 0.0054, 0.053, 0.1351, 0.2508, 0.4033, 0.5952, 0.7849, 0.9178, 0.9796, 1, 1, 1, 1, 1,
                         1, 1, 1,
                         1, 1, 1])

                    # Use probabilities for prediction (using linear interpolation)
                    input_value = df['estimated speed at hub height (m/s)']
                    df["Power(MW)"] = np.interp(input_value, data, probabilities) * self.rated_power

                    # Check if wind speed exceeds the cut-out speed
                    df.loc[input_value > self.cutout_speed, "Power(MW)"] = 0

                    # Check if wind speed is at least 5 m/s lower than the cut-out speed for restarting
                    restart_condition = (input_value <= (self.cutout_speed - 5))
                    df.loc[restart_condition, "Power(MW)"] = np.interp(input_value[restart_condition], data,
                                                                       probabilities) * self.rated_power

                    # adjust power based on air density
                    # Constants
                    # temperature_lapse_rate = 0.0065  # C/m (standard temperature lapse rate)
                    # gravity = 9.8  # m/s^2 (acceleration due to gravity)
                    # gas_constant = 8.314  # J/(mol·K) (universal gas constant)
                    # molar_mass_air = 0.0289644  # kg/mol (molar mass of air)

                    # Calculate temperature at hub height
                    surface_temperature = df["air temperature at 100m (C)"] + 273.15
                    surface_altitude = 100  # m
                    surface_pressure = df["air pressure at 100m (Pa)"]

                    df["hub temperature (K)"] = surface_temperature - (
                            self.temperature_lapse_rate * (self.hub_height - surface_altitude))

                    # Calculate pressure at hub height
                    pressure_ratio = np.exp(
                        (-self.gravity * self.molar_mass_air * (self.hub_height - surface_altitude)) /
                        (self.gas_constant * df["hub temperature (K)"])
                    )
                    # Calculate air density
                    df["hub pressure (Pa)"] = surface_pressure * pressure_ratio
                    df["hub air density"] = df["hub pressure (Pa)"] / (
                            287.058 * surface_temperature)  # J/kg·K specific gas constant for dry air
                    df["Adjust power based on air pressure (MW)"] = df["Power(MW)"] * df[
                        "hub air density"] / 1.225  # air density at sea level 15C

                    # Calculate P/Pr (Power correction ratio)
                    df["P/Pr"] = (df["Power(MW)"] / self.rated_power) * 100
                    df["P/Pr"] = df["P/Pr"].apply(lambda x: f"{x:.2f}%")
                    df["P/Pr(air density)"] = (df["Adjust power based on air pressure (MW)"] / self.rated_power) * 100
                    df["P/Pr(air density)"] = df["P/Pr(air density)"].apply(lambda x: f"{x:.2f}%")
                    Adjust_power_air_density = df["Adjust power based on air pressure (MW)"]
                    P_Pr_air_density = df["P/Pr(air density)"]
                    P_Pr = df["P/Pr"]
                    # Write the updated DataFrame to a new file
                    df.to_csv(new_file_path, index=False)
                elif 8.5 <= average_speed <= 10:
                    # Prepare data and probabilities
                    data = np.array(
                        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
                    probabilities = np.array(
                        [0, 0, 0, 0.0052, 0.0423, 0.1031, 0.1909, 0.3127, 0.4731, 0.6693, 0.8554, 0.964, 0.9942, 0.9994,
                         1, 1,
                         1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

                    # Use probabilities for prediction (using linear interpolation)
                    input_value = df['estimated speed at hub height (m/s)']
                    df["Power(MW)"] = np.interp(input_value, data, probabilities) * self.rated_power

                    # Check if wind speed exceeds the cut-out speed
                    df.loc[input_value > self.cutout_speed, "Power(MW)"] = 0

                    # Check if wind speed is at least 5 m/s lower than the cut-out speed for restarting
                    restart_condition = (input_value <= (self.cutout_speed - 5))
                    df.loc[restart_condition, "Power(MW)"] = np.interp(input_value[restart_condition], data,
                                                                       probabilities) * self.rated_power

                    # adjust power based on air density
                    # Constants (You can keep these constants since they don't change)
                    temperature_lapse_rate = 0.0065  # C/m (standard temperature lapse rate)
                    gravity = 9.8  # m/s^2 (acceleration due to gravity)
                    gas_constant = 8.314  # J/(mol·K) (universal gas constant)
                    molar_mass_air = 0.0289644  # kg/mol (molar mass of air)

                    # Calculate temperature at hub height
                    surface_temperature = df["air temperature at 100m (C)"] + 273.15
                    surface_altitude = 100  # m
                    surface_pressure = df["air pressure at 100m (Pa)"]

                    df["hub temperature (K)"] = surface_temperature - (
                            temperature_lapse_rate * (self.hub_height - surface_altitude))

                    # Calculate pressure at hub height
                    pressure_ratio = np.exp(
                        (-gravity * molar_mass_air * (self.hub_height - surface_altitude)) /
                        (gas_constant * df["hub temperature (K)"])
                    )
                    # Calculate air density
                    df["hub pressure (Pa)"] = surface_pressure * pressure_ratio
                    df["hub air density"] = df["hub pressure (Pa)"] / (
                            287.058 * surface_temperature)  # J/kg·K specific gas constant for dry air
                    df["Adjust power based on air pressure (MW)"] = df["Power(MW)"] * df[
                        "hub air density"] / 1.225  # air density at sea level 15C


                    # Calculate P/Pr (Power correction ratio)
                    df["P/Pr"] = (df["Power(MW)"] / self.rated_power) * 100
                    df["P/Pr"] = df["P/Pr"].apply(lambda x: f"{x:.2f}%")
                    df["P/Pr(air density)"] = (df["Adjust power based on air pressure (MW)"] / self.rated_power) * 100
                    df["P/Pr(air density)"] = df["P/Pr(air density)"].apply(lambda x: f"{x:.2f}%")
                    Adjust_power_air_density = df["Adjust power based on air pressure (MW)"]
                    P_Pr_air_density = df["P/Pr(air density)"]
                    P_Pr = df["P/Pr"]
                    # Write the updated DataFrame to a new file
                    df.to_csv(new_file_path, index=False)
                else:
                    data = np.array(
                        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
                    probabilities = np.array(
                        [0, 0, 0, 0.0043, 0.0323, 0.0771, 0.1426, 0.2329, 0.3528, 0.5024, 0.6732, 0.8287, 0.9264,
                         0.9774,
                         0.9946, 0.999, 0.999, 1, 1, 1, 1, 1, 1, 1, 1, 1])

                    # Use probabilities for prediction (using linear interpolation)
                    input_value = df['estimated speed at hub height (m/s)']
                    df["Power(MW)"] = np.interp(input_value, data, probabilities) * self.rated_power

                    # Check if wind speed exceeds the cut-out speed
                    df.loc[input_value > self.cutout_speed, "Power(MW)"] = 0

                    # Check if wind speed is at least 5 m/s lower than the cut-out speed for restarting
                    restart_condition = (input_value <= (self.cutout_speed - 5))
                    df.loc[restart_condition, "Power(MW)"] = np.interp(input_value[restart_condition], data,
                                                                       probabilities) * self.rated_power

                    # adjust power based on air density
                    # Constants (You can keep these constants since they don't change)
                    temperature_lapse_rate = 0.0065  # C/m (standard temperature lapse rate)
                    gravity = 9.8  # m/s^2 (acceleration due to gravity)
                    gas_constant = 8.314  # J/(mol·K) (universal gas constant)
                    molar_mass_air = 0.0289644  # kg/mol (molar mass of air)

                    # Calculate temperature at hub height
                    surface_temperature = df["air temperature at 100m (C)"] + 273.15
                    surface_altitude = 100  # m
                    surface_pressure = df["air pressure at 100m (Pa)"]

                    df["hub temperature (K)"] = surface_temperature - (
                            temperature_lapse_rate * (self.hub_height - surface_altitude))

                    # Calculate pressure at hub height
                    pressure_ratio = np.exp(
                        (-gravity * molar_mass_air * (self.hub_height - surface_altitude)) /
                        (gas_constant * df["hub temperature (K)"])
                    )
                    # Calculate air density
                    df["hub pressure (Pa)"] = surface_pressure * pressure_ratio
                    df["hub air density"] = df["hub pressure (Pa)"] / (
                            287.058 * surface_temperature)  # J/kg·K specific gas constant for dry air
                    df["Adjust power based on air pressure (MW)"] = df["Power(MW)"] * df[
                        "hub air density"] / 1.225  # air density at sea level 15C
                    # Calculate P/Pr (Power correction ratio)
                    df["P/Pr"] = (df["Power(MW)"] / self.rated_power) * 100
                    df["P/Pr"] = df["P/Pr"].apply(lambda x: f"{x:.2f}%")

                    df["P/Pr(air density)"] = (df["Adjust power based on air pressure (MW)"] / self.rated_power) * 100
                    df["P/Pr(air density)"] = df["P/Pr(air density)"].apply(lambda x: f"{x:.2f}%")
                    Adjust_power_air_density = df["Adjust power based on air pressure (MW)"]
                    P_Pr_air_density = df["P/Pr(air density)"]
                    P_Pr = df["P/Pr"]
                    df.to_csv(new_file_path, index=False)


                self.num_turbine = self.capacity / self.rated_power
                df["Adjust power based on air pressure (MW)"]=df["Adjust power based on air pressure (MW)"]*self.num_turbine
                float_adjust_power = df["Adjust power based on air pressure (MW)"].astype(float)
                float_annual_energy = float_adjust_power.sum()  # kWh per year
                float_p_pr = df["P/Pr(air density)"].str.rstrip('%').astype(float)
                self.annual_energy = float_annual_energy * (1 - self.wakeloss)  # with wake loss

                list_adjust_power = float_adjust_power.tolist()
                list_p_pr = float_p_pr.tolist()
                list_annual_energy = [float_annual_energy]  # Storing the sum in a list

                # # Writing output
                self.wind_gen = list_adjust_power #MWh per year
                self.wind_output = []
                #wind_output.append({"Name": "timestamp"})
                self.wind_output.append( {"Name": "Adjust power based on air density",
                                          "Value": list_adjust_power,
                                          "Unit": "kW"})
                self.wind_output.append({'Name': 'P/Pr based on air density',
                                         'Value': list_p_pr,
                                         'Unit': "%"})

               #LCOE of wind energy
                self.fcr=((self.inflation_rate * (1 + self.inflation_rate) ** self.lifetime) /
                          ((1 + self.inflation_rate) ** self.lifetime - 1))
                self.aep_net_kwh = self.annual_energy/(self.rated_power*self.num_turbine)
                self.wind_lcoe = (self.capex_per_kw * self.fcr + self.opex) / (self.aep_net_kwh) #$/kWh
                return self.wind_gen, self.wind_output,self.fcr,self.wind_lcoe


    # writing output to json
    def export_to_json(self):
        if self.wind_output:
            filename= 'wind_output.json'
            Wind_json_outfile = f'/Users/fengxiaotong/Desktop/wind power prediction/9.5三种方法的比较测算/test-组合/{filename}'
            with open(Wind_json_outfile, 'w') as outfile:
                json.dump(self.wind_output, outfile)
            print("done")
    # writing output to csv
    def export_to_csv(self):
        if self.wind_output:
            filename='wind_output.json'
            csvname = "wind_output.csv"
            Wind_outfile= f'/Users/fengxiaotong/Desktop/wind power prediction/9.5三种方法的比较测算/test-组合/{filename}'
            simulation_json_outfile = f'/Users/fengxiaotong/Desktop/wind power prediction/9.5三种方法的比较测算/test-组合/{filename}'
            simulation_csv_outfile = f'/Users/fengxiaotong/Desktop/wind power prediction/9.5三种方法的比较测算/test-组合/{csvname}'
            with open(simulation_json_outfile, 'w') as outfile:
                json.dump(self.wind_output, outfile)
            with open(simulation_json_outfile) as json_file:
                data = json.load(json_file)
                # now we will open a file for writing
            data_file = open(simulation_csv_outfile, 'w', newline='')
            # create the csv writer object
            csv_writer = csv.writer(data_file)

            csv_writer.writerow(["Location"])
            csv_writer.writerow(["Wind class",""])
            csv_writer.writerow(["Hub height",self.hub_height])
            csv_writer.writerow(["Cutin speed",self.cutin_speed])
            csv_writer.writerow(["Cutout speed",self.cutout_speed])
            count = 0
            time_series = []
            for i in data:

                # Writing data of CSV file
                if type(i["Value"]) != list:
                    csv_writer.writerow(i.values())
                else:
                    if i["Name"] != "Monthly water production":
                        time_series.append(i)

            header = []
            for i in time_series:
                header.append(i["Name"] + " (" + i["Unit"] + ")")

            csv_writer.writerow([])
            csv_writer.writerow(["Hour"] + header)
            for i in range(len(time_series[0]["Value"])):
                try:
                    csv_writer.writerow([i] + [j["Value"][i] for j in time_series])
                except:
                    continue
            data_file.close()
        print("done")



        # test wind

