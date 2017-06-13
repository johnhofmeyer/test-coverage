#!/
# john.hofmeyer@cadreon.com
# 09.07.2016
#
# Description:
# 

import mysql
import mysql.connector
import requests
import fileinput
import os
import sys
import time
import datetime
import json

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date
from sys import exit

## Global values
# sprintEpoch=18, the first sprint of 2016
# Epoch 01/04/2016 = day 1 of sprint 18
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

sprintEpoch=18
cadreonEpoch=date(2016,1,4)

def determineSprintNumber():
	today=date.today()
	thisMonday=today-timedelta(days=today.weekday()) # not really necessary, since we discard the remainder in the next calculation
	
	sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
	
	currentSprint=sprintEpoch+sprintsSinceEpoch

	return(currentSprint)

	
def determineSprintDay():
	today=date.today()
	daysSinceEpoch=(today-cadreonEpoch).days

	currentSprint=determineSprintNumber()
	sprintStart=(currentSprint-sprintEpoch)*14
	
	sprintDay=daysSinceEpoch-sprintStart
	if (sprintDay>4):
		sprintDay-=2
	
	return (sprintDay)
	
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	
	# Determine current sprint number, current Sprint day, and first day of Sprint 
	currentSprint=determineSprintNumber()
	sprintName="Sprint "+str(currentSprint)
	sprintDay=determineSprintDay()
	
	# Determine the first day of the sprint
	sprintFirstDay=str(cadreonEpoch+timedelta(days=(currentSprint-sprintEpoch)*14-1)) # Technically, this is the Sunday before the Sprint begins

	print "Current Sprint",currentSprint
	print "Sprint Day #",sprintDay
	
	# Get the list of all projects in TestRail
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	
	# Parse each project to determine if it has a current milestone associated
	for project in testRailProjects:
		
		#print project['name']
		projectID = str(project['id'])
		
		if (projectID != "27") :
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			
			for currentMilestone in projectMilestones:
				# If the milestone is current - then review the test runs associated to the milestone
				if (currentMilestone['name'].find(sprintName) > -1):
				
					milestoneID=currentMilestone['id']
					runs=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
					projectRuns=runs.json()
					
					print "Project: ", project['name']," id: ",str(project['id'])
					for run in projectRuns:
						if run['milestone_id'] == currentMilestone['id']:
							print run['name']

	
if __name__ == '__main__':
    main()