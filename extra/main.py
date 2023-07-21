from datetime import datetime, time
import datetime
import csv
import ast
import pandas as pd
import seaborn as sb
import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')

# Opening csv file

with open('Test_Data.csv', 'r') as csvFile:

    # reading csv file
    csv_reader = csv.DictReader(csvFile, delimiter='|')

    final_table_creation, hmap = [], {}
    for line in csv_reader:
        curr = {}
        # storing only that row which consists of system_check as source
        if line['Source'] == 'system_check':

            # converting systemhealth column string into dictionary
            system_health = ast.literal_eval(line['SystemHealth'])

            # storing date and time in hmap dictionary
            date, time = line['CreationDate'].split(" ")
            hmap["date"] = date
            hmap["time"] = time[:8]

            # storing cpu load in hmap dictionary
            for key in system_health["CPU"]:
                if key == 'CPU Load':
                    hmap[key] = float(system_health["CPU"][key]
                                      [:len(system_health["CPU"][key])-1])

            # storing ram usage in hmap dictionary
            for key in system_health['Ram Usage']:
                if key == 'Used Ram' or key == 'Total Ram':
                    hmap[key] = system_health['Ram Usage'][key]

            # storing disk usage in hmap dictionary
            for key in system_health['Disk Usage']:
                if key == 'Used Space Storage':
                    hmap['Used Disk'] = system_health['Disk Usage'][key]
                if key == 'Total Space Storage':
                    hmap['Total Disk'] = system_health['Disk Usage'][key]

            # storing swap space usage in hmap dictionary
            for key in system_health['Swap Space']:
                if key == 'Swap Space Percentage':
                    hmap[key] = float(system_health['Swap Space'][key][:len(
                        system_health['Swap Space'][key])-1])
            
            # storing this hmap into res array, basically this will represent one row of our new csv file
            for key in hmap:
                curr[key] = hmap[key]
            final_table_creation.append(curr)


# creating new csv file with name Final_Test_Data
with open('Final_Test_Data.csv', 'w', newline='') as csvFile:

    # creating column for new csv file using key stored in hmap
    fields = [key for key in hmap]

    # using DictWriter of csv module to write new csv file
    csv_writer = csv.DictWriter(csvFile, fieldnames=fields)
    csv_writer.writeheader()

    # creation of each row of new csv file
    for data in final_table_creation:
        csv_writer.writerow(data)


# Creation of datafram
data = pd.read_csv('Final_Test_Data.csv')

# Functions to convert string into integer and float


def modifyToInt(row):
    row = int(row.split(" ")[0])
    return row


def modifyToFloat(row):
    row = float(row.split(" ")[0])
    return row


data['Used Ram'] = data['Used Ram'].apply(modifyToInt)
data['Used Disk'] = data['Used Disk'].apply(modifyToInt)
data['Total Ram'] = data['Total Ram'].apply(modifyToInt)
data['Total Disk'] = data['Total Disk'].apply(modifyToInt)


# Creation of new columns showing Ram,Disk usage percentage


data['Used Ram Percentage'] = (data['Used Ram']*100)/data['Total Ram']
data['Used Disk Percentage'] = (data['Used Disk']*100)/data['Total Disk']
data.drop(['Used Ram', 'Used Disk', 'Total Ram',
          'Total Disk'], axis=1, inplace=True)
data.rename(columns={'time': 'Time', 'date': 'Date'}, inplace=True)
data['Date'] = pd.to_datetime(data['Date'])


# Plot between Ram Usage and time of three different dates

plt.figure(figsize=(15, 3))
sb.lineplot(data=data, x=data["Time"],
            y=data["Used Ram Percentage"], hue=data["Date"])


# Plot between Disk Usage and time of three different dates

plt.figure(figsize=(15, 5))
sb.scatterplot(data=data, x=data["Time"],
               y=data["Used Disk Percentage"], hue=data["Date"])


# Plot between CPU Usage and time of three different dates

plt.figure(figsize=(15, 5))
sb.lineplot(data=data, x=data["Time"], y=data["CPU Load"], hue=data["Date"])


# Plot between Ram, Disk and CPU Usage

plt.figure(figsize=(15, 5))
sb.pairplot(data[['Used Ram Percentage', 'Used Disk Percentage', 'CPU Load']])
