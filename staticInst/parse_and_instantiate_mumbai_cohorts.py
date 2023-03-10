#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#"""
#Copyright [2020] [Indian Institute of Science, Bangalore & Tata Institute of Fundamental Research, Mumbai]
#SPDX-License-Identifier: Apache-2.0
#"""
# Script for generating city files - instantiation of a synthetic city

import json
import geopandas as gpd
import pandas as pd
import math
from shapely.geometry import Point, MultiPolygon
from geopy.distance import geodesic

import warnings
warnings.filterwarnings('ignore')

import csv
import numpy as np
import random
import matplotlib.pyplot as plt


import argparse
import os
import sys

from computeDistributions import *

# Default Global Prameters
interactive = 0

default_miniPop = 10000
default_city="mumbai"
default_ibasepath = 'data/base/mumbai/'
default_obasepath = 'data/mumbai-10k/'

a_workplacesize = 3.26
c_workplacesize = 0.97
m_max_workplacesize = 2870
avgSchoolsize = 300

#fixing for now
slum_schoolsize_factor = 1
slum_householdsize_scalefactor = 1

#ppl working at sez and gov (Bangalore data)
max_sez=230000 /10
max_gov= (2295000*(12.327/66.84)*0.5) /10
max_ites = 1500000 /10
max_ites_not_sez=max_ites-max_sez

#counters
num_sez = 0
num_gov = 0
num_ites = 0

# Handling inputs and interactions
if interactive:
    city = default_city
    miniPop = default_miniPop
    ibasepath = default_ibasepath
    obasepath = default_obasepath
else:
    my_parser = argparse.ArgumentParser(description='Create mumbai_slums-as-wards for COVID-19 simulation')
#    my_parser.add_argument('-c', help='target city', default=default_city)
    my_parser.add_argument('-n', help='target population', default=default_miniPop)
#    my_parser.add_argument('-i', help='input folder', default=default_ibasepath)
    my_parser.add_argument('-o', help='output folder', default=default_obasepath)
    args = my_parser.parse_args()
    city = 'mumbai'
    miniPop = int(args.n)
    ibasepath = default_ibasepath   #args.i
    obasepath = args.o


# Workplace commute parameters
if city == 'bangalore':
    a_commuter_distance = 10.751
    b_commuter_distance = 5.384

else:
    a_commuter_distance = 4 #parameter in distribution for commuter distance - Thailand paper
    b_commuter_distance = 3.8  #parameter in distribution for commuter distance - Thailand paper


inputfiles = {
    "citygeojson":"city.geojson",
    "demographics":"demographics.csv",
    "employment":"employment.csv",
    "household":"households.csv",
    "cityprofile":"cityProfile.json",
    "train_route":"train_route.json",
    "travel_time":"travel_time.json"
             }
outputfiles = {
    "individuals":"individuals.json",
    "houses":"houses.json",
    "workplaces":"workplaces.json",
    "schools":"schools.json",
    "wardCentreDistance":"wardCentreDistance.json",
    "commonArea":"commonArea.json",
    "fractionPopulation":"fractionPopulation.json",
    "PRG_state":"PRG_state.log"
              }

#Check if the necessary files are present.
for f in inputfiles:
    assert os.path.isfile(os.path.join(ibasepath, inputfiles[f])), "File {} doesn't exist!".format(inputfiles[f])

inputfiles.update({
    "ODMatrix":"ODMatrix.csv"
                   })

for f in inputfiles:
    inputfiles[f] = os.path.join(ibasepath,inputfiles[f])


# Create output directory if not present
if not os.path.exists(obasepath):
    os.mkdir(obasepath)

for f in outputfiles:
    outputfiles[f] = os.path.join(obasepath,outputfiles[f])

with open(outputfiles["PRG_state"],"w+") as f:
    f.write(f"random.getstate():\n{str(random.getstate())}\n\n")
    f.write(f"np.random.get_state():\n{str(np.random.get_state())}\n")
print("Creating city with a population of approximately ",miniPop,flush=True)
print("")

# Read input data files
demographics = pd.read_csv(inputfiles["demographics"])
demographics['wardName'] = demographics['wardName'].values
demographics['totalPopulation'] = demographics['totalPopulation'].astype(int)
demographics = demographics.sort_values('wardNo')
nwards = demographics['wardIndex'].count()

households = pd.read_csv(inputfiles["household"])
households = households.sort_values("wardNo")
households['Households'] = households['Households'].astype(int)

employments = pd.read_csv(inputfiles["employment"])
employments = employments.sort_values("wardNo")
employments['Employed'] = employments['Employed'].astype(int)


hd_flag = 0
if 'hd_flag' in demographics.columns:
    hd_flag=1
else:
    hd_flag=0

def checkName(df, nwards=nwards,name="df"):
    if "wardName" not in df.columns:
        return
    for i in range(df.shape[0]):
        if df["wardName"].iloc[i] != demographics['wardName'].iloc[i]:
            print(f"WARNING: Check if this is a mismatch!")
            print(f"{i}\t {name}: {df['wardName'].iloc[i]}\t demographics: {demographics['wardName'].iloc[i]}")

def checkRows(df, nwards=nwards, name="df"):
    assert df.shape[0] == nwards,\
        f"Mismatch in {name}: num_rows is not {nwards}"
    for i in range(nwards):
        assert df["wardNo"].iloc[i] == i+1,\
            f"Mismatch in {name}: row {i+1} has wardNo {df['wardIndex'].iloc[i]}"
    checkName(df,nwards=nwards,name=name)


# In[ ]:


if os.path.exists(os.path.join(ibasepath,'presampled-points')):
    presampledflag = 1
    print("Lat-longs presampled. Will be using those.")
else:
    presampledflag=0
    print("Reading city.geojson to get ward polygons...",end='',flush=True)
    geoDF = gpd.read_file(inputfiles["citygeojson"])
    geoDF['wardNo'] = geoDF['wardNo'].astype(int)
    geoDF['wardIndex'] = geoDF['wardNo'] - 1
    geoDF = geoDF[['wardIndex','wardNo', 'wardName', 'geometry']]
    geoDF['wardBounds'] = geoDF.apply(lambda row: MultiPolygon(row['geometry']).bounds, axis=1)
    geoDF = geoDF.sort_values('wardNo')
    ##!! Note that the geojson file has coordinates in (longitude, latitude) order!
    geoDF['wardCentre'] = geoDF.apply(lambda row: (MultiPolygon(row['geometry']).centroid.x, MultiPolygon(row['geometry']).centroid.y), axis=1)
    checkRows(geoDF, nwards=24, name="city.geojson")


# In[ ]:

print("Checking for mismatches...", end="", flush=True)
checkRows(demographics, name="demographics")
checkRows(households, name="households")
checkRows(employments, name="employments")
print("done", flush=True)

# In[ ]:


with open(inputfiles["cityprofile"], newline='') as file:
    cityprofiledata = json.load(file)

m_max_commuter_distance = cityprofiledata['maxWorkplaceDistance']


hbins = cityprofiledata['householdSize']['bins']
hweights = cityprofiledata['householdSize']['weights']
hweights[0]=hweights[0] + 1- sum(hweights) #Just do a slight adjustment in case they don't sum to 1

def sampleHouseholdSize():
    s = np.random.choice(hbins,1,p=hweights)[0]
    if '+' in s:
        n = int(s[:-1])
    elif '-' in s:
        (a,b) = s.split('-')
        n = random.randint(int(a),int(b))
    else:
        n = int(s)
    return n

agebins = cityprofiledata['age']['bins']
ageweights = cityprofiledata['age']['weights']
ageweights[0] = ageweights[0] + 1 - sum(ageweights) #Just do a slight adjustment in case they don't sum to 1

def sampleAge():
    s = np.random.choice(agebins,1,p=ageweights)[0]
    if '+' in s:
        n = int(s[:-1])
    else:
        (a,b) = s.split('-')
        n = random.randint(int(a),int(b))
    return n

schoolsizebinweights = [float(a) for a in cityprofiledata['schoolsSize']['weights']]
schoolsizebinweights[0] = schoolsizebinweights[0] + 1 - sum(schoolsizebinweights)
def sampleSchoolSize():
    s = int(np.random.choice(list(range(len(cityprofiledata['schoolsSize']['bins']))),1,p=schoolsizebinweights)[0])
    return (100*s + random.randint(0,99))


totalPop = demographics['totalPopulation'].sum()
scale = miniPop/totalPop

demographics['employed_frac'] = employments["Employed"] / demographics['totalPopulation']
demographics["totalPopulation"] = demographics["totalPopulation"]*scale


# In[ ]:


presampledpoints = []
if presampledflag:
    for i in range(nwards):
        dftmp = pd.read_csv(os.path.join(ibasepath,"presampled-points",str(i)+".csv"),names=["lat","lon"])
        dftmp["lat"] = dftmp["lat"].astype(float)
        dftmp["lon"] = dftmp["lon"].astype(float)
        presampledpoints.append(dftmp)

def sampleRandomLatLong(wardIndex):
    if presampledflag:
        i = random.randint(0,len(presampledpoints[wardIndex])-1)
        (lat,lon) = presampledpoints[wardIndex].loc[i]
        return (round(lat, 4), round(lon, 4))
    else:
        (lon1,lat1,lon2,lat2) = geoDF['wardBounds'][wardIndex]
        wardPoly = MultiPolygon(geoDF['geometry'][wardIndex])
        while True:
            lat = round(random.uniform(lat1,lat2), 4)
            lon = round(random.uniform(lon1,lon2), 4)
            point = Point(lon,lat) #IMPORTANT: Point takes in order of longitude, latitude
            if wardPoly.contains(point):
                return (lat,lon)


def distance(lat1, lon1, lat2, lon2):
    p1 = (lat1, lon1)
    p2 = (lat2, lon2)
    d = geodesic(p1, p2).km
    return round(d, 2)


communityCentres = []
for i in range(nwards):
    (lat,lon) = sampleRandomLatLong(i)
    communityCentres.append((lat,lon))

def getCommunityCenterDistance(lat,lon,wardIndex):
    (latc,lonc) = communityCentres[wardIndex]
    return distance(lat,lon,latc,lonc)


# In[ ]:


if os.path.exists(inputfiles['ODMatrix']):
    ODMatrix = pd.read_csv(inputfiles['ODMatrix'])

    checkRows(ODMatrix, name="ODMatrix")
    cols = [a for a in ODMatrix.columns if a != "wardNo"]
    for i in range(nwards):
        assert int(cols[i]) == i+1,\
            f"Mismatch in ODMatrix.csv: col {i+1} has {cols[i]}"

    _ = ODMatrix.pop("wardNo")
    ODMatrix = ODMatrix.values
else:
    print("ODMatrix not found. Using uniform ODmatrix.",flush=True)
    ODMatrix = [[(1/nwards) for _ in range(nwards)] for _ in range(nwards)]
for i in range(nwards):
    ODMatrix[i][0] = ODMatrix[i][0] + 1 - sum(ODMatrix[i])
    #Adjust in case the rows don't sum to 1


# Train & cohorts setup
route_df = pd.read_json(inputfiles["train_route"])
travel_df = pd.read_json(inputfiles["travel_time"])

def findRoadTime(aerial_distance):
    # https://www.cartoq.com/traffic-speeds-indias-fastest-slowest-cities/
    avg_road_speed_kmph = 21.6
    # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3835347/
    aerial_road_detour_index = 1.7 # Increase for India compared to US.
    road_distance =  aerial_distance * aerial_road_detour_index
    road_time_min = road_distance * 60.0 / avg_road_speed_kmph
    return road_time_min

def findShortestTrainRoute(lat1, lon1, lat2, lon2):
    # Returns time in minutes via train, closest src station, closest dest station
    route_src_df = route_df.copy()
    route_dest_df = route_df.copy()
    route_src_df['station_distance'] = route_src_df.apply(lambda x: distance(lat1, lon1, x.latitude, x.longitude),axis=1)
    route_dest_df['station_distance'] = route_src_df.apply(lambda x: distance(lat2, lon2, x.latitude, x.longitude),axis=1)
    route_src_df.sort_values(by=['station_distance'], ascending=True, inplace=True, ignore_index=True)
    route_dest_df.sort_values(by=['station_distance'], ascending=True, inplace=True, ignore_index=True)

    route_src_df = route_src_df.loc[:3]
    route_src_df['station_time'] = route_src_df.apply(lambda x: findRoadTime(x.station_distance), axis=1)
    route_dest_df = route_dest_df.loc[:3]
    route_dest_df['station_time'] = route_dest_df.apply(lambda x: findRoadTime(x.station_distance), axis=1)

    route_src_df['merge_key'] = 1
    route_dest_df['merge_key'] = 1
    route_train_df = route_src_df.merge(route_dest_df, on='merge_key', suffixes=('_src', '_dest'))
    route_train_df['train_time'] = route_train_df.apply(lambda x:
        travel_df[(travel_df.start == x.stationId_src) & (travel_df.end == x.stationId_dest)].travel_time_min.values[0], axis=1)
    route_train_df['total_time'] = route_train_df.apply(lambda x: x.station_time_src + x.train_time + x.station_time_dest, axis=1)

    route_train_df.sort_values(by=['total_time'], ascending=True, inplace=True, ignore_index=True)
    return route_train_df.loc[0].total_time, route_train_df.loc[0].stationId_src, route_train_df.loc[0].stationId_dest


def willTakeTrain(lat1,lon1,lat2,lon2):
    # Returns if train will be preferred option of travel between src and dest,
    # along with src, dest station id
    aerial_distance_km = distance(lat1,lon1,lat2,lon2)
    # For short distances default to road.
    if aerial_distance_km <= 1.0:
        return False, None,None
    road_time_min = findRoadTime(aerial_distance_km)
    train_time_min, src, dest = findShortestTrainRoute(lat1, lon1, lat2, lon2)
    if src == dest:
        return False, None,None

    # Favor trains, for cost parity of trains, or frequency of buses.
    road_travel_cost_factor = 2.5
    if road_time_min*road_travel_cost_factor < train_time_min:
        return False, None, None

    return True, src, dest




#Now the real city building begins

#Creating houses

print("Creating households for each ward...",end='',flush=True)
houses = []
hid = 0
for wardIndex in range(nwards):
    pop = demographics["totalPopulation"][wardIndex]
    currpop = 0

    #creating houses
    while(currpop < pop):
        h = {}
        h["id"]=hid
        h["wardIndex"]=wardIndex

        if hd_flag:
            h["slum"] = int(demographics["hd_flag"][wardIndex])

        s = sampleHouseholdSize()
        h["size"]=s
        currpop+=s

        (lat,lon) = sampleRandomLatLong(wardIndex)
        h["lat"] = lat
        h["lon"] = lon

        houses.append(h)
        hid+=1
print("done.",flush=True)


# In[ ]:


print("Creating individuals to populate the households...",end='',flush=True)

pid = 0
individuals = []
workers = [[] for _ in range(nwards)]
schoolers = [[] for _ in range(nwards)]

wardpop_actual = [0 for _ in range(nwards)]
totalPop_actual = 0

for h in houses:
    s = h["size"]
    for i in range(s):
        p = {"id":pid}

        p["household"]=h["id"]
        wardIndex = h["wardIndex"]
        p["wardIndex"]=wardIndex
        p["wardNo"] = wardIndex+1
        if hd_flag:
            p["slum"] = h["slum"]

        p["lat"] = h["lat"]
        p["lon"] = h["lon"]

        p["CommunityCentreDistance"] = getCommunityCenterDistance(h["lat"],h["lon"],wardIndex)

        age = sampleAge()
        p["age"] = age

        #initialising most stuff to None
        p["employed"]=None
        p["workplace"]=None
        p["workplaceType"]=0
        p["school"]=None
        p["startStation"]=None
        p["endStation"]=None

        if age < 3:
            p["employed"]=0
            p["workplaceType"] = 0
        elif age >= 3 and age < 15 :
            #decide about his/her school
            p["employed"]=0
            p["workplaceType"]=2 #this is school

            #assuming they all go to school
            schoolers[wardIndex].append(pid)

        elif age >= 15 and age < 65:
            #decide about employment
            eprob = demographics['employed_frac'][wardIndex]
            eprobadjusted = eprob/sum([ageweights[a] for a in range(3,13)])
            if(random.uniform(0,1)<eprobadjusted):
                #person is employed
                p["employed"]=1

                p["workplace"]="TODO"
                workplaceward = int(np.random.choice(list(range(nwards)),1,p=ODMatrix[wardIndex])[0])
                p["workplaceward"]=workplaceward
                p["workplaceType"]=1
                workers[workplaceward].append(pid)
            else:
                p["employed"]=0
                if age < 20:
                    p["workplaceType"]=2
                    #All the unemployed in this age bracket go to school
                    schoolers[wardIndex].append(pid)
                else:
                    p["workplaceType"] = 0

                p["employed"]=0
                p["workplaceType"]=0
        else:
            #decide about seniors
            p["employed"]=0
        individuals.append(p)
        wardpop_actual[p["wardIndex"]]+=1
        totalPop_actual+=1
        pid+=1


print("done.",flush=True)



def workplaces_size_distribution(a=3.26, c=0.97, m_max=2870):
    count=1
    a=3.26
    c=0.97
    m_max=2870
    p_nplus = np.arange(float(m_max))
    for m in range(m_max):
        p_nplus[m] =  ((( (1+m_max/a)/(1+m/a))**c) -1) / (((1+m_max/a)**c) -1)

    p_nminus = 1.0 - p_nplus
    p_n = np.arange(float(m_max))
    prev=0.0
    for m in range(1, m_max):
        p_n[m] = p_nminus[m] - prev
        prev = p_nminus[m]

    return p_n/sum(p_n)

def sampleWorkplaceSize():
    wsdist = workplaces_size_distribution()
    m_max = len(wsdist)
    return int(np.random.choice(np.arange(m_max),1,p=wsdist)[0])

officeType = {"Other":0,"SEZ":1,"Government":2,"IT":3,"Construction":4,"Medical":5}

#Old code = for roll-back
#def sampleOfficeType(size):
    #For now completely ignoring the size and just returning officetype at random
    #return officeType[random.choice(list(officeType.keys()))]

def sampleOfficeType(size):
    global num_gov, num_ites, num_sez
    #Large workplace at SEZs, officeType=1
    if num_sez < max_sez and size >= 200 and size < 300 and np.random.binomial(1,0.7):
        num_sez += size
        return  officeType['SEZ']
    elif num_sez < max_sez and size >= 300 and size < 400 and np.random.binomial(1,0.8):
        num_sez += size
        return  officeType['SEZ']
    elif num_sez < max_sez and size >= 400 and size < 500 and np.random.binomial(1,0.9):
        num_sez += size
        return  officeType['SEZ']
    elif num_sez < max_sez and size >= 500:
        num_sez += size
        return  officeType['SEZ']

    #Government offices
    elif size >= 20 and num_gov < max_gov:
        num_gov += size
        return  officeType['Government']

    #IT/ITES
    elif size >= 10 and num_ites <= max_ites_not_sez:
        num_ites += size
        return  officeType['IT']

    else:
        return  officeType['Other']



print("Assigning schools...",end='', flush=True)

#assigning school to people who want go to school
schools = []
sid = 0
for wardIndex in range(nwards):
    while len(schoolers[wardIndex])>0: #some unassigned kids left in the ward
        #Set up basic facts about school
        s = {"ID":sid} #capitalised in the previous code so keeping it so
        s["wardIndex"]=wardIndex
        (lat,lon) = sampleRandomLatLong(wardIndex)
        s["lat"] = lat
        s["lon"] = lon
        if hd_flag==1:
            s["slum"]=int(demographics["hd_flag"][wardIndex])

        size = int(sampleSchoolSize())

        #Fill up school with kids
        i = 0
        while(i < size and len(schoolers[wardIndex])>0):
            pid = schoolers[wardIndex].pop(random.randrange(len(schoolers[wardIndex])))
            individuals[pid]["school"]=sid
            i+=1
        schools.append(s)
        sid+=1
        #Note: This sort of creates a very skewed first-bracket for school size.
        #If the city size is small, then many schools will be "under-capacity".
        #Need to think about how to fix this corner case.
print("done.",flush=True)


# In[ ]:


print("Assigning workplaces to people...",end='',flush=True)

#assigning workplaces to people who want work
workplaces = []
wid = sid
for wardIndex in range(nwards):
    wworkers = len(workers[wardIndex])
    while len(workers[wardIndex])>0:
        w = {"id":wid}
        (lat,lon) = sampleRandomLatLong(wardIndex)
        w["lat"] = lat
        w["lon"] = lon

        w["wardIndex"]=wardIndex
        s = sampleWorkplaceSize()
        oType = sampleOfficeType(s)
        w["officeType"]=oType

        i = 0
        while(i < s and len(workers[wardIndex])>0):
            pid = workers[wardIndex].pop(random.randrange(len(workers[wardIndex])))
            individuals[pid]["workplace"]=wid
            isTrain, srcStationId, destStationId = willTakeTrain(individuals[pid]["lat"],individuals[pid]["lon"],w["lat"], w["lon"])
            if isTrain:
                individuals[pid]["startStation"] = srcStationId
                individuals[pid]["endStation"] = destStationId
            del individuals[pid]["workplaceward"]
            i+=1
        workplaces.append(w)
        wid+=1

print('done.',flush=True)



# Stats of instantiated city
print("")
print("Number of wards:",nwards)
print("Created (mini)city")
print("Population:",len(individuals))
print("Households:",len(houses))
print("Schools:",len(schools))
print("Workplaces:",len(workplaces))
print("")

# Assigning Common Areas
commonAreas = []
for i in range(nwards):
    c = {"ID":i}
    c["wardNo"] = i+1
    (lat,lon)= communityCentres[i]
    c["lat"] = lat
    c["lon"] = lon
    commonAreas.append(c)

fractionPopulations = []
for i in range(nwards):
    w = {"wardNo":i+1}
    w["totalPopulation"] = int(wardpop_actual[i])
    w["fracPopulation"] = wardpop_actual[i]/totalPop_actual
    fractionPopulations.append(w)

wardCentreDistances = [ {"ID":i+1} for i in range(nwards)]
for i in range(nwards):
    for j in range(nwards):
        d = distance(commonAreas[i]["lat"],commonAreas[i]["lon"],commonAreas[j]["lat"],commonAreas[j]["lon"])
        wardCentreDistances[i][str(j+1)]=d




# Create dataframes for validation
df1 = pd.DataFrame(individuals)
del individuals

# Creating instantiated city files as JSONs
print("Dumping to json files...",end='',flush=True)

f = open(outputfiles['houses'], "w+")
f.write(json.dumps(houses))
f.close
print("houses.json, ",end='',flush=True)

f = open(outputfiles['workplaces'], "w+")
f.write(json.dumps(workplaces))
f.close
print("workplaces.json, ",end='',flush=True)
wp = pd.DataFrame(workplaces)


f = open(outputfiles['schools'], "w+")
f.write(json.dumps(schools))
f.close
print("schools.json, ",end='',flush=True)

f = open(outputfiles['commonArea'], "w+")
f.write(json.dumps(commonAreas))
f.close
print("commonArea.json, ",end='',flush=True)

f = open(outputfiles['fractionPopulation'], "w+")
f.write(json.dumps(fractionPopulations))
f.close
print("fractionPopulation.json, ",end='',flush=True)

f = open(outputfiles['wardCentreDistance'], "w+")
f.write(json.dumps(wardCentreDistances))
f.close
print("wardCentreDistance.json, ",end='',flush=True)


del wardCentreDistances, commonAreas, fractionPopulations, schools, houses, workplaces

df1.to_json(outputfiles['individuals'], orient='records')
print("individuals.json ... done.",flush=True)

print('\nGenerating validation plots for the instantitaion...\n')

# Get distributions to match
age_values, age_distribution = compute_age_distribution(cityprofiledata['age']['weights'])
household_sizes, household_distribution = compute_household_size_distribution(cityprofiledata['householdSize']['bins'], cityprofiledata['householdSize']['weights'])
schoolsize_values, schoolsize_distribution = extrapolate_school_size_distribution(cityprofiledata['schoolsSize']['weights'],avgSchoolsize)
workplacesize_distribution = workplaces_size_distribution()

print("Validating age distribution in instantiation...",end='',flush=True)
plt.plot(df1['age'].value_counts(normalize=True).sort_index(ascending=True), 'r-o',label='Instantiation')
plt.plot(age_distribution, 'b-',label='Data')
plt.xlabel('Age')
plt.ylabel('Density')
plt.title('Distribution of age')
plt.grid(True)
plt.legend()
plt.xticks(np.arange(0,81,10), np.concatenate((age_values[np.arange(0,71,10)], ['80+'])) )
plt.savefig(os.path.join(obasepath, 'age.png'))
plt.close()
print("done.",flush=True)

print("Validating household-size in instantiation...",end='',flush=True)
house = df1['household'].value_counts().values
unique_elements, counts_elements = np.unique(house, return_counts=True)
counts_elements = counts_elements / np.sum(counts_elements)
plt.plot(counts_elements, 'r-o', label='Instantiation')
plt.plot(household_distribution, 'b-', label='data')
plt.xlabel('Household-size')
plt.ylabel('Density')
plt.title('Distribution of household-size')
plt.grid(True)
plt.legend()
plt.xticks(np.arange(0,len(household_sizes),1), np.concatenate((age_values[np.arange(1,household_sizes[-1],1)], [str(household_sizes[-1])+'+'])) )
plt.savefig(os.path.join(obasepath,'household_size.png'))
plt.close()
print("done.",flush=True)

print("Validating school-size in instantiation...",end='',flush=True)
schoolsizeDistribution = cityprofiledata['schoolsSize']['weights']
full_frame = np.floor(np.array([len(np.where(df1['school'] == i)[0]) for i in np.unique(df1['school'].values)[~np.isnan(np.unique(df1['school'].values))]])/100).astype(int)
schoolsize_output = [len(np.where(full_frame == j)[0]) for j in np.arange(0,len(schoolsizeDistribution))] / np.sum([len(np.where(full_frame == j)[0]) for j in np.arange(0,len(schoolsizeDistribution))])
plt.plot(schoolsize_output,'r-o', label='Instantiation')
plt.plot(schoolsizeDistribution,'b-', label='Data')
xlabel = np.arange(0,len(schoolsizeDistribution))
plt.xticks(xlabel, np.concatenate((np.arange(1,10)*100, [str('901+')])))
plt.xlabel('School size')
plt.ylabel('Density')
plt.legend()
plt.title('Distribution of school size')
plt.grid(True)
plt.savefig(os.path.join(obasepath, 'school_size.png'))
plt.close()
print("done.",flush=True)


# generate workplace size distribution
a=a_workplacesize
c=c_workplacesize
m_max=m_max_workplacesize
workplace_sizes = np.arange(m_max)
p_nplus = np.arange(float(m_max))
for m in range(m_max):
    p_nplus[m] =  ((( (1+m_max/a)/(1+m/a))**c) -1) / (((1+m_max/a)**c) -1)

p_nminus = 1.0 - p_nplus
p_n = np.arange(float(m_max))
prev=0.0
for m in range(1, m_max):
    p_n[m] = p_nminus[m] - prev
    prev = p_nminus[m]


# workplace size
print("Validating workplace-size in instantiation...",end='',flush=True)

full_frame = np.array([len(np.where(df1['workplace'] == i)[0]) for i in np.unique(df1['workplace'].values)[~np.isnan(np.unique(df1['workplace'].values))]])
workplacesize_output = [len(np.where(full_frame == j)[0]) for j in workplace_sizes] / np.sum([len(np.where(full_frame == j)[0]) for j in workplace_sizes])
workplace_distribution = p_n
plt.plot(np.log10(workplace_sizes),np.log10(workplacesize_output),'r',label='Instantiation')
plt.plot(np.log10(workplace_sizes), np.log10(workplace_distribution),label='Model')
plt.xlabel('Workplace size (log-scale)')
plt.ylabel('log_10 Density')
plt.title('Distribution of workplace size (in log-scale)')
plt.grid(True)
plt.legend()
plot_xlabel =  [1, 10, 100, 1000, 2400]
plot_xlabel1 = np.log10(workplace_sizes)[plot_xlabel]
plt.xticks(plot_xlabel1, (workplace_sizes)[plot_xlabel])
plt.savefig(os.path.join(obasepath,'workplace_size.png'))
plt.close()
print("done.",flush=True)


print("Validating workplace commute distance in instantiation...",end='',flush=True)
full_frame = np.array([distance(df1.loc[i,'lat'],df1.loc[i,'lon'],wp.loc[(wp.index+sid)==int(df1.loc[i,'workplace']),'lat'].values[0],wp.loc[(wp.index+sid)==int(df1.loc[i,'workplace']),'lon'].values[0]) for i in np.where(df1['workplaceType']==1)[0]])
commuter_distance_output = [len(np.where(np.array(np.floor(full_frame),dtype=int) ==i)[0]) for i in np.arange(0,m_max_commuter_distance)]/np.sum([len(np.where(np.array(np.floor(full_frame),dtype=int) ==i)[0]) for i in np.arange(0,m_max_commuter_distance)])
actual_dist=[]
actual_dist = travel_distance_distribution(0,m_max_commuter_distance,a_commuter_distance,b_commuter_distance)
d = np.arange(0,m_max_commuter_distance,1)
plt.plot(np.log10(d),np.log10(actual_dist),'b-',label='Model')
plt.plot(np.log10(d),np.log10((commuter_distance_output)),'r-o',label='Instantiation')
plt.xlabel('Workplace distance (km) (log-scale)')
plt.ylabel('log_10 Density')
plt.title('Distribution of workplace distances')
plot_xlabel=[1,5,25,31]
plot_xlabel1 = np.log10(d)[plot_xlabel]
plt.xticks(plot_xlabel1,d[plot_xlabel])
plt.grid(True)
plt.legend()
plt.savefig(os.path.join(obasepath,'workplace_distance.png'))
plt.close()
print("done.",flush=True)
