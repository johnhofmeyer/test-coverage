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
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+' AND issuetype!=Bug","fields":["id","key","priority","created","summary","status","reporter"]}'
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
	
	# both the INSERT and UPDATE queries use the same data set
	# data=deferred_count, created_today, critical, major, medium, minor, new_bugs, resolved, in_progress, in_review, verified, reopened, closed, sprint_number, sprint_day, jira_project
	
	insert_result=("INSERT INTO defects "
               "(production, closed_deferred, deferred_count, created_today, critical, major, medium, minor, new_bugs, resolved, in_progress, in_review, verified, reopened, closed, sprint_number, sprint_day, jira_project) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
			   
	update_result=("UPDATE defects "
				   "SET production = %s, closed_deferred= %s, deferred_count = %s, created_today = %s, critical = %s, major = %s, medium = %s, minor = %s, new_bugs = %s, resolved = %s, in_progress = %s, in_review = %s, verified = %s, reopened = %s, closed = %s"
				   "WHERE sprint_number = %s AND sprint_day = %s AND jira_project= %s"
				   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
	
	
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
		#print severity,status,deferred,reportedToday
		
		#productDefects[project]["deferred"]=getDeferredBugs(project)['total']
		deferred=getDeferredBugs(project)['total']
		closedDeferred=getClosedDeferred(project)['total']
		print project,
		currentBugs=getCurrentBugs(project)
		for bug in currentBugs:
			#print bug
			#sys.exit()
			bugDetail=requests.get(bug['self'], headers=APIHeaders, auth=jiraAuth)
			bugFields=bugDetail.json()['fields']

			if (bugDetail.json()['fields']['customfield_12723'] != None):
				if (bugDetail.json()['fields']['customfield_12723']['value'] == 'Production'):
					production+=1
					print "p",
			
			print bugFields
			parentStory=bugFields['issuelinks']['inwardIssue']['issuetype']
			
			bugStatus=bug['fields']['status']['name']
			#productDefects[project]["status"][bugStatus]+=1
			status[bugStatus]+=1
			
			if (bugStatus != "Closed"):
				bugSeverity=bug['fields']['priority']['name']
				#productDefects[project]["severity"][bugSeverity]+=1
				severity[bugSeverity]+=1
			
			bugCreated=bug['fields']['created']
			if (today in bug['fields']['created']):
				#productDefects[project]["createdToday"]+=1
				reportedToday+=1
			print ".",
		print '\n'
		
		count_data=(currentSprint, sprintDay, project,)
		query_data=(production, closedDeferred, deferred, reportedToday, severity['Critical'], severity['Major'], severity['Medium'], severity['Minor-Low'], status['Resolved'], status['New'], status['In Progress'], status['In Review'], status['Reopened'], status['Verified'], status['Closed'], currentSprint, sprintDay, project)
		# data=deferred_count, created_today, critical, major, medium, new_bugs, resolved, in_progress, in_review, verified, reopened, closed, sprint_number, sprint_day, jira_project


		cursor.execute(count_query,count_data)
		for rowCount in cursor:
			resultCount=rowCount[0]

		if (resultCount>0):
			cursor.execute("UPDATE defects "
				   "SET production = "+str(production)+", closed_deferred="+str(closedDeferred)+", deferred_count ="+str(deferred)+", created_today = "+str(reportedToday)+", critical = "+str(severity['Critical'])+", major = "+str(severity['Major'])+", medium = "+str(severity['Medium'])+", minor = "+str(severity['Minor-Low'])+", new_bugs = "+str(status['New'])+", resolved = "+str(status['Resolved'])+", in_progress = "+str(status['In Progress'])+", in_review = "+str(status['In Review'])+", verified = "+str(status['Verified'])+", reopened = "+str(status['Reopened'])+", closed = "+str(status['Closed'])+""
				   "WHERE sprint_number = "+str(currentSprint)+" AND sprint_day = "+str(sprintDay)+" AND jira_project= "+project+"",
				   "VALUES (%s), "+str(production)+"")
			#cursor.execute(update_result, query_data)
			db.commit()
		else:
			cursor.execute(insert_result, query_data)
			db.commit()
		
		
	#print productDefects
	cursor.close()
	db.close()
	
if __name__ == '__main__':
    main()
	