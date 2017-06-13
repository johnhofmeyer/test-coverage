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

def firstDayPreviousRelease()
	releaseSprint=determineSprintNumber()-2
	if (releaseSprint%2 == 0):  ## we want the first day of the odd numbered sprint
		releaseSprint-=1
	firstDayPreviousRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayPreviousRelease)
	
def firstDayOfSprint():
	sprintNumber=determineSprintNumber()
	firstDayOfSprint=str(cadreonEpoch+timedelta(days=(sprintNumber-sprintEpoch)*14-1))
	return(firstDayOfSprint)

def getPreviousReleaseDefects(project):
	startDate=firstDayPreviousRelease()
	endDate=firstDaySinceLastRelease()
	
	sprintDayZero=firstDayOfSprint()
	defectBacklogFilter='{"jql":"project='+project+' AND issuetype=Bug AND created >= '+startDate+' AND created <= '+endDate+' AND BugType=Production Bugs","fields":["id","key","priority","created","summary","status","reporter"]}'
	deferedBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectBacklogFilter, headers=APIHeaders, auth=jiraAuth)
	deferredBugList=deferedBugs.json()
	return(deferredBugList
	
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

	
def getProductionBugs(project):
#project=PLAT and issuetype=Bug and "Bug type"="Production Bug"
	lookbackDate=firstDayPreviousRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND "Bug type"="Production Bug" AND created > '+lookbackDate+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
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
	
	# Connect to coverage database
	db=mysql.connector.connect(user='admin', password='admin',host='127.0.0.1',database='coverage',buffered=True)
	cursor=db.cursor()
	
	# define queries for defects
	count_query= ("SELECT Count(*) from defects WHERE sprint_number = %s and sprint_day = %s and jira_project = %s ;")
	# count data = sprint_number, sprint_day, project, run_name
	
	
	insert_result=("INSERT INTO stories "
					"(sprint_number, sprint_day, jira_project,total_points, total_stories,total_bugs,stories_without_estimates,storypoints_without_estimates, stories_without_points) "
					"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
	
	
	storyStatus={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	projectStatus={"totalPoints" : 0.0,"taskCount":0,"storyCount":0, "storyStatus" : storyStatus, "pointsDueToday" : 0.0, "pointsPastDue" : 0.0, "storiesWithoutDueDates" : 0}
	
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
	
	for project in productStatus:
		# reset defect counts
		severity={'Critical': 0, 'Major': 0, 'Medium': 0, 'Minor-Low' : 0}
		status={'New':0, 'In Progress':0, 'In Review':0, 'Resolved':0, 'Reopened':0, 'Verified':0, 'Closed':0}
		deferred=0
		reportedToday=0
		closedDeferred=0
		production=0
		#print severity,status,deferred,reportedToday
		
		
		sprintTickets=getProductionBugs(project)
		totalTickets=sprintTickets['total']

		
		print project,totalTickets,"Tickets"
		for ticket in sprintTickets['issues']:
			
			ticketKey=ticket['key']
			ticketSummary=ticket['fields']['summary']
			#print ticket['key'],ticket['fields']['summary'],
			
			ticketDetail=requests.get(ticket['self'], headers=APIHeaders, auth=jiraAuth)
			details=ticketDetail.json()
			
			ticketDueDate=details['fields']['duedate']
			ticketStoryPoints=details['fields']['customfield_10002']
			if (ticketStoryPoints is None) : ticketStoryPoints=0.0
			ticketType=details['fields']['issuetype']['name']
			if (ticketType == "Bug") : totalBugs+=1
			if (ticketType == "Story") : totalStories+=1
			
			totalSprintPoints+=ticketStoryPoints
			if ("eployment" not in ticketSummary):
				if (ticketType=="Story" and ticketStoryPoints <1) : noPoints+=1
				if (ticketType=="Story" and ticketDueDate is None) : 
					noEstimates+=1
					noEstimatePoints+=ticketStoryPoints
			print ".",
		
		print 
		print "Total Points: ",totalSprintPoints
		print "Total Stories: ",totalStories
		print "Total Bugs: ",totalBugs
		print "Stories without Estimates: ",noEstimates
		print "Total Points w/o Estimates : ",noEstimatePoints
		print "Stories without points: ",noPoints
			
		print
		
		result_data=(currentSprint, sprintDay, project, totalSprintPoints,totalStories,totalBugs,noEstimates,noEstimatePoints,noPoints)
		
		cursor.execute(insert_result, result_data)
		db.commit()

if __name__ == '__main__':
    main()
	