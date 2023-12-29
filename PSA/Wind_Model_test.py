import os
import csv
import math
import numpy as np
import pandas as pd
import json


class Wind:
    # INPUT VARIABLES
    temperature_lapse_rate = 0.0065  # C/m (standard temperature lapse rate)
    gravity = 9.8  # m/s^2 (acceleration due to gravity)
    gas_constant = 8.314  # J/(mol·K) (universal gas constant)
    molar_mass_air = 0.0289644  # kg/mol (molar mass of air)
    folder_path = '/Users/fengxiaotong/Desktop/sedat_model_selection-main/wind_speed'

    def __init__(self, hub_height=80, rated_power=1.8, cutin_speed=3, cutout_speed=20, folder_path=''):
        # input
        self.hub_height = hub_height
        self.rated_power = rated_power
        self.cutin_speed = cutin_speed
        self.cutout_speed = cutout_speed
        self.folder_path = '/Users/fengxiaotong/Desktop/wind power prediction/9.5三种方法的比较测算/test-组合'
        self.timestamp = ""

    # output
    # output value
    # performance parameters

    def windpower(self):

        file_list = os.listdir(self.folder_path)
        for file_name in file_list:
            if file_name.endswith('.csv'):
                file_path = os.path.join(self.folder_path, file_name)
                new_file_path = os.path.join(self.folder_path, f"new_{file_name}")

                # Open the original CSV file and the new file
                with open(file_path, 'r') as file, open(new_file_path, 'w', newline='') as new_file:
                    reader = csv.reader(file)
                    writer = csv.writer(new_file)

                    rows = list(reader)  # read all rows

                    # Append six data at the end of the first row
                    rows[1].extend(
                        ['alpha', 'estimated speed at hub height (m/s)', "hub temperature (K)", "hub pressure (Pa)",
                         "hub air density",
                         'Power(MW)', "Adjust power based on air pressure (MW)", 'P/Pr', "P/Pr(air density)",
                         'Rated Power', '2MW', 'Cut-in speed', 'm/s', 'Cut-out speed', 'm/s'])

                    # create new file
                    writer.writerows(rows)

                print(f"Created new file: {new_file_path}")

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
                    Adjust_power_air_density=df["Adjust power based on air pressure (MW)"]

                    # Calculate P/Pr (Power correction ratio)
                    df["P/Pr"] = (df["Power(MW)"] / self.rated_power) * 100
                    df["P/Pr"] = df["P/Pr"].apply(lambda x: f"{x:.2f}%")
                    P_Pr = df["P/Pr"]
                    df["P/Pr(air density)"] = (df["Adjust power based on air pressure (MW)"] / self.rated_power) * 100
                    df["P/Pr(air density)"] = df["P/Pr(air density)"].apply(lambda x: f"{x:.2f}%")
                    P_Pr_air_density = df["P/Pr(air density)"]
                    # Writing output
                    wind_output = []
                    wind_output.append({"Name": "Adjust power based on air density", "Value": Adjust_power_air_density, 'Unit': 'MW'})
                    wind_output.append({'Name': 'P/Pr based on air density','Value':P_Pr_air_density,'Unit':"%"})
                    return wind_output
                    # Write the updated DataFrame to a new file
                    #df.to_csv(new_file_path, index=False)
                #filename = self.wind + '_wind_output' + self.timestamp + '.json'
                #design_json_outfile = f'/tmp/results/{filename}'
                #with open(design_json_outfile, 'w') as outfile:
                    #json.dump(self.wind_output, outfile)
                print('wind model executed')