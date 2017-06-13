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

jiraAuth=HTTPBasicAuth('Jay.Chakraborty@cadreon.com','YOUR-PASSWORD-HERE')
APIHeaders={'Content-Type': 'application/json'}

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
	
def firstDaySinceLastRelease():
	releaseSprint=determineSprintNumber()
	if (releaseSprint%2 == 0):  ## we want the first day of the odd numbered sprint
		releaseSprint-=1
	firstDayLastRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayLastRelease)

def firstDayOfSprint():
	sprintNumber=determineSprintNumber()
	firstDayOfSprint=str(cadreonEpoch+timedelta(days=(sprintNumber-sprintEpoch)*14-1))
	return(firstDayOfSprint)
	
def getDeferredBugs(project):
	sprintDayZero=firstDayOfSprint()
	defectBacklogFilter='{"jql":"project='+project+' AND issuetype=Bug AND created < '+sprintDayZero+' AND status != Closed","fields":["id","key","priority","created","summary","status","reporter"]}'
	deferedBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectBacklogFilter, headers=APIHeaders, auth=jiraAuth)
	deferredBugList=deferedBugs.json()
	return(deferredBugList)
	
def getClosedDeferred(project):
	releaseDayZero=firstDaySinceLastRelease()
	sprintDayZero=firstDayOfSprint()
	defectBacklogFilter='{"jql":"project='+project+' AND issuetype=Bug AND created < '+sprintDayZero+' AND Resolved > '+sprintDayZero+' AND status=Closed","fields":["id","key","priority","created","summary","status","reporter"]}'
	deferedBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectBacklogFilter, headers=APIHeaders, auth=jiraAuth)
	deferredBugList=deferedBugs.json()
	return(deferredBugList)

def getCurrentBugs(project):
	sprintDayZero=firstDayOfSprint()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND created > '+sprintDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth)
	bugList=currentBugs.json()

	return(bugList['issues'])

def getSprintTickets(project):
	currentSprint=determineSprintNumber()
	# Filter out bugs, since we already have a detailed defect count
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+' AND issuetype!=Bug","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth)
	projectList=projectSprint.json()
	
	return (projectList)
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv	
	
	
	
	storyStatus={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	projectStatus={"totalPoints" : 0.0,"taskCount":0,"storyCount":0, "storyStatus" : storyStatus, "pointsDueToday" : 0.0, "pointsPastDue" : 0.0}
	
	jiraProductList={"CCS" : "Cadreon Console Shell", "RNB" : "Reporting and Billing (Datorama)", "AR":"Ramp Ranker", "CCCM" : "Cadreon Console Campaign Management", "CCR" : "Cadreon Console Reports", "CADMKT" : "Cadreon Marketplace", "AMU" : "AMP UI", "UTAG" : "Cadreon Unity Tag", "ADE" : "AMP Data Engine", "CSF" : "Cadreon Salesforce Integration", "PLAT" : "Cadreon Platform"}
	
	severity={'Critical': 0, 'Major': 0, 'Medium': 0, 'Minor-Low' : 0}
	status={'New':0, 'In Progress':0, 'In Review':0, 'Resolved':0, 'Reopened':0, 'Verified':0, 'Closed':0}
	
	sprintDefects={"severity" : severity, "status" : status, "deferred":0, "createdToday" : 0, "closedDeferred" : 0, "production" : 0}
	productDefects={"CCS" : sprintDefects, "RNB" : sprintDefects, "AR":sprintDefects, "CCCM" : sprintDefects, "CCR" : sprintDefects, "CADMKT" : sprintDefects, "AMU" : sprintDefects, "UTAG" : sprintDefects, "ADE" : sprintDefects, "CSF" : sprintDefects, "PLAT" : sprintDefects}
	productStatus={"CCS" : projectStatus, "RNB" : projectStatus, "AR":projectStatus, "CCCM" : projectStatus, "CCR" : projectStatus, "CADMKT" : projectStatus, "AMU" : projectStatus, "UTAG" : projectStatus, "ADE" : projectStatus, "CSF" : projectStatus, "PLAT" : projectStatus}
	
	# Determine current sprint number, current Sprint day, and first day of Sprint 
	today=str(date.today())
	currentSprint=determineSprintNumber()
	sprintName="Sprint "+str(currentSprint)
	sprintDay=determineSprintDay()
	
	# Determine the first day of the sprint
	sprintFirstDay=str(cadreonEpoch+timedelta(days=(currentSprint-sprintEpoch)*14-1)) # Technically, this is the Sunday before the Sprint begins

	print "Current Sprint",currentSprint
	print "Sprint Day #",sprintDay

	# Defect Count per project - including backlog defects
	
	for project in productDefects:
		# reset defect counts
		severity={'Critical': 0, 'Major': 0, 'Medium': 0, 'Minor-Low' : 0}
		status={'New':0, 'In Progress':0, 'In Review':0, 'Resolved':0, 'Reopened':0, 'Verified':0, 'Closed':0}
		deferred=0
		reportedToday=0
		closedDeferred=0
		production=0

		deferred=getDeferredBugs(project)['total']
		closedDeferred=getClosedDeferred(project)['total']
		print project,
		currentBugs=getCurrentBugs(project)
		for bug in currentBugs:

			bugDetail=requests.get(bug['self'], headers=APIHeaders, auth=jiraAuth)

			if (bugDetail.json()['fields']['customfield_12723'] != None):
				if (bugDetail.json()['fields']['customfield_12723']['value'] == 'Production'):
					production+=1
					print "p",
			
			parentStory=bug['fields']['issuelinks']['inwardIssue']['issuetype']
			
			bugStatus=bug['fields']['status']['name']
			status[bugStatus]+=1
			
			if (bugStatus != "Closed"):
				bugSeverity=bug['fields']['priority']['name']
				severity[bugSeverity]+=1
			
			bugCreated=bug['fields']['created']
			if (today in bug['fields']['created']):
				reportedToday+=1
			print ".",
		print '\n'
		

	
	
if __name__ == '__main__':
    main()
	