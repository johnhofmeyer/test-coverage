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

jiraAuth=HTTPBasicAuth('john.hofmeyer@cadreon.com','6s!NNER6')
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
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+'","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth)
	projectList=projectSprint.json()
	
	return (projectList)
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv	
	

	
	productList=["CCS", "AR", "CCCM", "CCR", "CADMKT", "AMU", "UTAG", "ADE", "CSF", "PLAT"] # "RNB" is excluded, becuase it is not part of the Unity deploy
	
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
	
	for project in productList:

		print project

		sprintTickets=getSprintTickets(project)

		#print jirProj,totalTickets,"Tickets"
		for ticket in sprintTickets['issues']:
		
			ticketKey=ticket['key']
			ticketSummary=ticket['fields']['summary']
			#print ticket['key'],ticket['fields']['summary'],
			
			if ("eployment" in ticketSummary):
				print "https://projects.mbww.com/browse/"+ticketKey
				ticketDetail=requests.get(ticket['self'], headers=APIHeaders, auth=jiraAuth)
				deployContent=ticketDetail.json()['fields']['description']
				
				print deployContent
				#sys.exit()
				print
											


if __name__ == '__main__':
    main()
	