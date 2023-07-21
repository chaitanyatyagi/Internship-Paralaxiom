from collections import defaultdict
import pandas as pd


with open("./platform.log", 'r') as file:
    dataSet = file.readlines()

n = len(dataSet)
dataOne,dataTwo = defaultdict(list),defaultdict(list)

for idx in range(110,n):
    each = dataSet[idx][110:].split(",")
    
    # Condition for first csv file
    if each[0] == 'Ended' or each[0] == 'nded':
        checkpoint = each[2].split(" --> ")[1]
        # If checkpoint type is not inside_zone we will not proceed
        if checkpoint == "inside_zone":

            # getting data
            time = each[1].split(" --> ")[0][1:]
            frameId = each[1].split(" --> ")[2]
            objectId = each[3].split(" --> ")[1]
            correctObjectId = ""
            for i in objectId:
                if i == "n":
                    break
                correctObjectId += i

            # making json for first csv
            dataOne['Frame-Id'].append(frameId)
            dataOne['Object-Id'].append(correctObjectId[:-1])
            dataOne['Time-Taken'].append(time)
            dataOne['Check-Point-Type'].append(checkpoint)
    
    # Condition for second csv file
    elif each[0][:7] == 'FrameId' or each[0][:6] == 'rameId':
         # getting data
        frameId = each[0].split(" --> ")[1]
        objectNo = each[1].split(" --> ")[1]
        timeTaken = each[2].split(" --> ")[1][:-1]
        correctTimeTaken = ""
        for i in timeTaken:
            if i == "n":
                break
            correctTimeTaken += i

        # making json for second csv
        dataTwo['Frame-Id'].append(frameId)
        dataTwo['Number-Of-Objects'].append(objectNo)
        dataTwo['Time-Taken'].append(correctTimeTaken[:-1])
        



df = pd.DataFrame.from_dict(dataOne, orient='index').transpose()
df.to_csv('csv1.csv')

df = pd.DataFrame.from_dict(dataTwo, orient='index').transpose()
df.to_csv('csv2.csv')


