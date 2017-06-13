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

user="vRestAutoAPI"
passWord="cadreon123"

jenkinsUser="john.hofmeyer"
jenkinsAPIToken="7ef40b73178fe27db33af8aec620558e"

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

def getAuthentication(env,user,passWord):

	apiHost="qa-api.cadreon.com"
	if (env=="stage"):
		apiHost="stage-api.cadreon.com"
	if (env=="prod"):
		apiHost="cadreon-api.cadreon.com"
	
	params="grant_type=password&username="+user+"&password="+passWord
	url="https://"+apiHost+"/token?"+params
	headerValues={"Accept": "application/json, text/plain, */*","Origin": "https://qa-app.cadreon.com","Authorization": "Basic V0Y5aGxBY2Y4T1ppSDllY3BJY3hYTXdMNlNZYTp1VzdzZHF0OFRZV0NfVURXVkVxZEQ4c09Zd1Fh","Content-Type": "application/x-www-form-urlencoded"}
	
	login=requests.post(url,headers=headerValues)
	loginBody=login.json()
	authToken=loginBody['access_token']
	return (authToken)
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	# Connect to coverage database
	db=mysql.connector.connect(user='admin', password='admin',host='127.0.0.1',database='coverage',buffered=True)
	cursor=db.cursor()
	componentCursor=db.cursor()
	
	projectQuery= ("SELECT jira_project, project "
				  "FROM projectmapping;")
	
	componentQuery= ("SELECT component, versionMethod, jenkinsProject "
				  "FROM componentmapping WHERE project=%s;")
	
	# Determine current sprint number, current Sprint day, and first day of Sprint 
	currentSprint=determineSprintNumber()
	sprintName="Sprint "+str(currentSprint)
	sprintDay=determineSprintDay()
	
	# Determine the first day of the sprint
	sprintFirstDay=str(cadreonEpoch+timedelta(days=(currentSprint-sprintEpoch)*14-1)) # Technically, this is the Sunday before the Sprint begins

	print "Current Sprint",currentSprint
	print "Sprint Day #",sprintDay
	
	## auth & header for QA environment - used to capture version numbers through the API
	authToken=getAuthentication("qa",user,passWord)
	headerValues={"Accept": "application/json, text/plain, */*","Origin": "https://qa-app.cadreon.com","Authorization": "Bearer "+str(authToken),"Cad-Market": "US","Content-Type": "application/x-www-form-urlencoded","User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"}
	
	qa="https://qa-api.cadreon.com"
	
	## Jenkins Host with Basic Authorization
	jenkinsHost="http://"+jenkinsUser+":"+jenkinsAPIToken+"@jenkins.cadreonint.com"
	
	cursor.execute(projectQuery, )
	for (jira_project, project) in cursor:
		print "Project: ",project
		
		#componentCursor.execute(componentQuery, project )
		componentCursor.execute("SELECT component, versionMethod, jenkinsProject FROM componentmapping WHERE project='"+jira_project+"';",)
		for (component, versionMethod, jenkinsProject) in componentCursor:
		
			## Jenkins Path for QA Project:
			## /job/unity/{{jenkinsProject}}/api/json
			jenkinsAPI="/job/"+jenkinsProject+"/deploy-qa/api/json"
			if (jenkinsProject == "unity-scrapers"):
				jenkinsAPI="/job/"+jenkinsProject+"/qa-deploy/api/json"
				#Path is different for unity-scraper
				#/job/unity-scrapers/qa-deploy/api/json
			
			jenkinsQABuildPromotion=jenkinsHost+jenkinsAPI

			componentQAPromotion=requests.get(jenkinsQABuildPromotion)
			if (componentQAPromotion.status_code >299):
				print jenkinsQABuildPromotion
				print componentQAPromotion.status_code
			componentInfo=componentQAPromotion.json()
			lastSuccessBuild=componentInfo['id']
			buildLink=componentInfo['url']
			promotionLink="http://jenkins.cadreonint.com/job/"+jenkinsProject+"/"+lastSuccessBuild+"/promotion/"
			#print "Promotion Link: ",promotionLink
	
			if (versionMethod!=None):
				if ('.json' in versionMethod):
					versionInfo=requests.get("https://qa-app.cadreon.com"+versionMethod,headers=headerValues)

					if (versionInfo.status_code<300):
						buildInfo=versionInfo.json()
						buildNumber=buildInfo['metadata']['build']
						version=buildInfo['metadata']['version']
						buildArtifact=jira_project
					else:
						buildInfo="Not Available API Response: ",versionInfo.status_code
						buildNumber="Not Available API Response: ",versionInfo.status_code
						version="Not Available API Response: ",versionInfo.status_code
				else: 
					versionInfo=requests.get("https://qa-api.cadreon.com"+versionMethod,headers=headerValues)
						
					if (versionInfo.status_code<300):
						buildInfo=versionInfo.json()
						buildNumber=buildInfo['build']['jenkinsBuildNumber']
						version=buildInfo['build']['productVersion']
						buildArtifact=buildInfo['artifact']['name']
					else:
						buildInfo="Not Available API Response: ",versionInfo.status_code
						buildNumber="Not Available API Response: ",versionInfo.status_code
						version="Not Available API Response: ",versionInfo.status_code

				print "	Component: ",component," Build Artifact: ",buildArtifact," Jenkins QA Build: ",lastSuccessBuild,"  API Build: ",buildNumber," Release Version: ",version 
			else:
				print "	Component: ",component," Jenkins QA Build: ",lastSuccessBuild
	

	
if __name__ == '__main__':
    main()