#!/
# john.hofmeyer@cadreon.com
# 09.12.2016
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
import statistics
import base64

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date

## Global values
# sprintEpoch=18, the first sprint of 2016
# Epoch 01/04/2016 = day 1 of sprint 18
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

sprintEpoch=18
cadreonEpoch=date(2016,1,4)
daysInSprint=14

user="vRestAutoAPI"
passWord="cadreon123"

jenkinsUser="john.hofmeyer"
jenkinsAPIToken="7ef40b73178fe27db33af8aec620558e"
jenkinsHost="http://"+jenkinsUser+":"+jenkinsAPIToken+"@jenkins.cadreonint.com"

APIHeaders={'Content-Type': 'application/json'}

db=mysql.connector.connect(user='daily_stats', password='yVgvQM7NU&vJXj6637D9',host='qa-daily-stats.ckvgpujcycok.us-east-1.rds.amazonaws.com',database='coverage',buffered=True)
pythonCursor=db.cursor()

acceptableDeferedRate=12.5

def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def decode(key, enc):
	dec = []
	enc = base64.urlsafe_b64decode(enc)
	for i in range(len(enc)):
		key_c = key[i % len(key)]
		dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
		dec.append(dec_c)
	return "".join(dec)

def determineSprintNumber():
	today=date.today()
	thisMonday=today-timedelta(days=today.weekday()) # not really necessary, since we discard the remainder in the next calculation
	
	sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
	
	currentSprint=sprintEpoch+sprintsSinceEpoch

	return(currentSprint)

def determineReleaseNumber():
	currentSprint=determineSprintNumber()
	releaseNumber=currentSprint/2
	if (currentSprint%2 == 1):
		releaseNumber+=1
	
	return("2."+str(releaseNumber))
	
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
	if (releaseSprint > 41):
		if (releaseSprint%2 == 0):  ## we want the first day of the odd numbered sprint
			releaseSprint-=1

	firstDayLastRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayLastRelease)

def firstDayOfPreviousRelease():
	releaseSprint=determineSprintNumber()
	if (releaseSprint%2 != 0):  ## we want the first day of the odd numbered sprint
		releaseSprint-=1
	firstDayLastRelease=str(cadreonEpoch+timedelta(days=(releaseSprint-sprintEpoch)*14-1))
	return(firstDayLastRelease)

def getOpenedBugsCount(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND created > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

	bugList=currentBugs.json()
	return(bugList['total'])

def getResolvedBugsNotFromBacklog(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND created > '+releaseDayZero+' AND resolved > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	bugList=currentBugs.json()
	return(bugList['total'])	

def getAllResolvedBugs(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12723] != \\"Production Bug\\" AND resolved > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	bugList=currentBugs.json()
	return(bugList['total'])	

def getRegressionBugsCount(project):
	releaseDayZero=firstDaySinceLastRelease()
	defectFilter='{"jql":"project='+project+' AND issuetype=Bug AND cf[12727]= \"Regression Test\" AND created > '+releaseDayZero+' ","fields":["id","key","priority","created","summary","status","reporter"]}'
	currentBugs=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())

	bugList=currentBugs.json()
	return(bugList['total'])
	
def getSprintTickets(project):
	currentSprint=determineSprintNumber()
	# Get all of the tickets in the current Sprint
	projectFilter='{"jql":"Sprint = '+project+'-'+str(currentSprint)+'","fields":["id","key","priority","created","summary","status","reporter"]}'
	projectSprint=requests.post("https://projects.mbww.com/rest/api/2/search", data=projectFilter, headers=APIHeaders, auth=jiraAuth())
	projectList=projectSprint.json()
	print projectList['total']," tickets"

	return (projectList)

def getProductionDefects():
	releaseDayZero=firstDaySinceLastRelease()
	# Get all of the tickets in the current Sprint
	defectFilter='{"jql":"filter = ProductSet AND issuetype = bug AND cf[12723] = \\"Production Bug\\" AND created >= '+releaseDayZero+'","fields":["id","key","priority","created","summary","status","reporter"]}'

	defectRequest=requests.post("https://projects.mbww.com/rest/api/2/search", data=defectFilter, headers=APIHeaders, auth=jiraAuth())
	defectList=defectRequest.json()
	print defectList['total']," Production Defects"
	return (defectList)
	
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

def getNetworkAuth():
	theNumber='9'
	unWord='54mzpbTE'
	theWord=decode("theWord",unWord)
	return theNumber+theWord+theNumber

def jiraAuth():
	return(HTTPBasicAuth('john.hofmeyer@cadreon.com',getNetworkAuth()))
	
def severityColor(calculation,defaultColor="black"):
	# black is default (100%) unless otherwise specified
	theColor='"color: rgb(0,0,0);"'   # Black is the absence of color
	if (defaultColor == "green"):	#  green - 100%
		theColor='"color: rgb(0,153,0);"'
	if (calculation<1): # grey - below 100%
		theColor='"color: rgb(140,140,140);"'
	if (calculation<.90): # Yellow - below 90%
		theColor='"color: rgb(255,153,0);"'
	if (calculation<.51): # red - 50% or less
		theColor='"color: rgb(255,0,0);"'
	
	return (theColor)
	
def updateDefectTable(projectCursor,sprintNumber, sprintDay, project, defectCounts):
	defectStatus={}
	sprintYesterday=int(sprintDay)-1
	#defectStatus={"New":0, "In Progress":0, "In Review":0, "Resolved":0, "Reopened":0, "Verified":0, "Closed":0}
	#print sprintNumber, sprintDay,project,defectCounts
	for key in defectCounts:
		defectStatus.update({key:{"today":defectCounts[key],"yesterday":0}})

	projectCursor.execute("SELECT Count(*) from defects WHERE sprint_number = "+sprintNumber+" and sprint_day = "+sprintDay+" and jira_project = '"+project+"'; ",)
	resultCount=0
	for rowCount in projectCursor:
		resultCount=rowCount[0]
		
	if (resultCount>0): # If the row exists, perform an UPDATE
		projectCursor.execute("UPDATE defects SET newDefects = "+str(defectCounts['New'])+" , inDev = "+str(defectCounts['In Progress'])+" , reopened = "+str(defectCounts['Reopened'])+" , inReview = "+str(defectCounts['In Review'])+" , inQA = "+str(defectCounts['Resolved'])+" , verified = "+str(defectCounts['Verified'])+" , closed = "+str(defectCounts['Closed'])+""
			"WHERE sprint_number = "+str(sprintNumber)+" AND sprint_day = "+str(sprintDay)+" AND project= "+project+"",
			"VALUES (%s)",str(sprintNumber))	
			
	else:	 # if the row does not exist, perform an INSERT
		projectCursor.execute("INSERT into defects "
		"(sprint_number, sprint_day, jira_project, newDefects, inDev, reopened, inReview, inQA, verified, closed) "
		"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(str(sprintNumber), str(sprintDay), project, defectCounts['New'], defectCounts['In Progress'], defectCounts['Reopened'], defectCounts['In Review'], defectCounts['Resolved'], defectCounts['Verified'], defectCounts['Closed']))

	db.commit()
	
	# capture the metrics, related to defects
	if (sprintYesterday > -1):
		projectCursor.execute("SELECT newDefects, inDev, reopened, inReview, inQA, verified, closed from defects WHERE sprint_number = "+sprintNumber+" and sprint_day = "+str(sprintYesterday)+" and jira_project = '"+project+"'; ",)
		for (newDefects,inDev,inReview,inQA,reopened,verified,closed) in projectCursor:
			if newDefects is None: newDefects=0
			if inDev is None: inDev=0
			if inReview is None: inReview=0
			if inQA is None: inQA=0
			if reopened is None: reopened=0
			if verified is None: verified=0
			if closed is None: closed=0
			if reopened is None: reopened=0
			
			defectStatus["New"]["yesterday"]=newDefects
			defectStatus["In Progress"]["yesterday"]=inDev
			defectStatus["In Review"]["yesterday"]=inReview
			defectStatus["Resolved"]["yesterday"]=inQA
			defectStatus["Reopened"]["yesterday"]=reopened
			defectStatus["Verified"]["yesterday"]=verified
			defectStatus["Closed"]["yesterday"]=closed
			defectStatus["Reopened"]["yesterday"]=reopened
	
	return defectStatus

def getCertificationPage():
	# determines if a certification page should be updated
	# If certPage=[CERTIFICATION PAGE] is found, it will be updated
	# If certPage with no argument passed, function will determine latest cert page
	# If there is no certPage argument passed, it will return a False value
	for argVal in sys.argv:
		if (argVal.find("certPage") > -1):	# 
			if (argVal.find("certPage=") >-1):
				return argVal.split("=")[1]
			else:
				return("Cadreon+Release+"+determineReleaseNumber()+"+Certification")
	return (False)

def getTestCoverage(coverageQuery,projectName,sprintNumber=determineSprintNumber(),sprintDay=determineSprintDay()):
	resultVals={"today":0,"yesterday":0,"trend":0,"sixMonth":0}
	coverageResults={}
	
	todayResult=dbCoverageRequest(coverageQuery,projectName,sprintNumber,sprintDay)
	yesterdayResult=dbCoverageRequest(coverageQuery,projectName,sprintNumber,sprintDay-1)
	trendResult=dbCoverageRequest(coverageQuery,projectName,sprintNumber-1,sprintDay)
	sixMonthResult=dbCoverageRequest(coverageQuery,projectName,sprintNumber-11,sprintDay)
	
	for key in todayResult:
		coverageResults.update({key:{"today":todayResult[key],"yesterday":yesterdayResult[key],"trend":trendResult[key],"sixMonth":sixMonthResult[key]}})
		
	return(coverageResults)

def dbCoverageRequest(coverageQuery,projectName,sprintNumber,sprintDay):
	if (sprintDay < 0):
		return {"passed":0,"failed":0,"blocked":0,"untested":0,"total":0,"executed":0}
	pythonCursor.execute(coverageQuery,(projectName,sprintNumber,sprintDay))
	for (passed, failed, blocked, untested) in pythonCursor:
		if passed is None:
			passed=0
		if failed is None:
			failed=0
		if blocked is None:
			blocked=0
		if untested is None:
			untested=0
		totalTests=passed+failed+blocked+untested
		executed=totalTests-untested
	return({"passed":passed,"failed":failed,"blocked":blocked,"untested":untested,"total":totalTests,"executed":executed})
	
def updateJiraTable(projectCursor,tableName, sprintNumber, sprintDay, project, jiraValues):
	#storyStatus={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	#storyPoints={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	
	tName="storypoints"
	
	projectCursor.execute("SELECT Count(*) from "+tName+" WHERE sprint_number = "+sprintNumber+" and sprint_day = "+sprintDay+" and jira_project = '"+project+"'; ",)
	resultCount=0
	for rowCount in projectCursor:
		resultCount=rowCount[0]
		
	if (resultCount>0):
		projectCursor.execute("UPDATE "+tName+" SET newDefects = "+str(jiraValues['New'])+" , ready = "+str(jiraValues['Ready'])+" , inDev = "+str(jiraValues['In Progress'])+" , reopened = "+str(jiraValues['Reopened'])+" , inReview = "+str(jiraValues['In Review'])+" , inQA = "+str(jiraValues['Resolved'])+" , verified = "+str(jiraValues['Verified'])+" , closed = "+str(jiraValues['Closed'])+""
			"WHERE sprint_number = "+str(sprintNumber)+" AND sprint_day = "+str(sprintDay)+" AND project= "+project+"",
			"VALUES (%s)",str(sprintNumber))
		#print "UDPATE JIRA "+tName
	else:
	  	projectCursor.execute("INSERT into "+tName+" "
		"(sprint_number, sprint_day, jira_project, newStories, ready, inDev, reopened, inReview, inQA, verified, closed) "
		"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(str(sprintNumber), str(sprintDay), project, jiraValues['New'], jiraValues['Ready'], jiraValues['In Progress'], jiraValues['Reopened'], jiraValues['In Review'], jiraValues['Resolved'], jiraValues['Verified'], jiraValues['Closed']))
		#print "INSERT JIRA "+tName
	
	db.commit()
	
	return


	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	#print 'Number of arguments:', len(sys.argv), 'arguments.'
	#print 'Argument List:', str(sys.argv)
	
	jiraAuth=HTTPBasicAuth('john.hofmeyer@cadreon.com',getNetworkAuth())
	
	
	# Status colors
	green='"color: rgb(0,153,0);"'
	yellow='"color: rgb(255,153,0);"'
	red='"color: rgb(255,0,0);"'
	grey='"color: rgb(240,240,240);"'
	black='"color: rgb(255,255,255);"'
	
	# Connect to coverage database
	#db=mysql.connector.connect(user='admin', password='admin',host='127.0.0.1',database='coverage',buffered=True)
	cursor=db.cursor()
	defectCursor=db.cursor()
	subCursor=db.cursor()
	functTestCursor=db.cursor()
	autoRegres=db.cursor()
	autoCursor=db.cursor()
	componentCursor=db.cursor()
	projectCursor=db.cursor()
	
	# Determine current sprint number and sprint day
	currentSprint=determineSprintNumber()
	previousSprint=currentSprint-1
	nextSprint=currentSprint+1
	
	
	sprintName='Sprint '+str(currentSprint)
	sprintDay=determineSprintDay()
	
	dayOneForFilter=str(firstDaySinceLastRelease())
	
	######################################################################################################
	##
	## Production Issues Table
	prodIssuesHeader='<p></p><p>Production Issues</p>'
	prodIssuesHeader+='<div><table>'
	prodIssuesHeader+='<colgroup><col/><col/><col/><col/></colgroup><tbody>'
	prodIssuesHeader+='<tr><th class="confluenceTh">Project</th>'
	prodIssuesHeader+='<th class="confluenceTh">Reported since Last Release</th>'
	prodIssuesHeader+='<th class="confluenceTh">Reported this Sprint</th>'
	prodIssuesHeader+='<th class="confluenceTh">Reported Today</th></tr>'
	
	prodIssues=prodIssuesHeader
	
	######################################################################################################
	##
	## Certification Table
	
	certTableHeader='<p></p><p></p><p>Path to Certification</p>'
	certTableHeader+='<div><table>'
	certTableHeader+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
	certTableHeader+='<tr><th class="confluenceTh">Test Areas</th>'
	certTableHeader+='<th class="confluenceTh">(A) Total TC</th>'
	certTableHeader+='<th class="confluenceTh">(B) TC executed</th>'
	certTableHeader+='<th class="confluenceTh"><p>(C) % TC Executed</p><h6 id="TestCoveragePercentage"><span style="color: rgb(51,102,255);">(B/A)* 100</span></h6></th>'
	certTableHeader+='<th class="confluenceTh">(D) TC Passed</th>'
	certTableHeader+='<th class="confluenceTh"><p>(E) % TC Passed</p><h6 id="TestCoveragePercentage"><span style="color: rgb(51,102,255);">(D/A)* 100</span></h6></th>'
	certTableHeader+='<th class="confluenceTh"><p>(F) Open Bugs</p><p>w/ High Priority</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(G) Bugs found</p><p>in this cycle</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(H) Bugs resolved excluding bugs from backlog</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(I) Bugs resolved including bugs from backlog</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>(J) % Bugs Deferred</p><p>excluding bugs from backlog</p><h6 id="CoverageforCurrentSprintDay-((G-H)/G)*100"><span style="color: rgb(51,102,255);">((G - H)/G) * 100</span></h6></th>'
	certTableHeader+='<th class="confluenceTh"><p>(K) % Bugs Deferred</p><p>including bugs from backlog</p><h6 id="CoverageforCurrentSprintDay-((G-I)/G)*100"><span style="color: rgb(51,102,255);">((G - I)/G) * 100</span></h6></th>'
	certTableHeader+='<th class="confluenceTh"><p>Meet Criteria?</p><p>Threshold for this release is '+str(acceptableDeferedRate)+'%</p></th>'
	certTableHeader+='<th class="confluenceTh"><p>Staging Acceptance Tests Pass</p><p><span style="color: rgb(51,153,102);">pass</span>: yes</p><p><span style="color: rgb(255,0,0);">fail</span>: list JIRA ticket(s)</p></th></tr>'

	certTable='<p> </p><hr/><p> </p>'+certTableHeader
	
	confluenceBody='<p><h2>'+sprintName+' | Sprint Day '+str(sprintDay+1)+'</h2></p>'
	
	certificationPage='<h2 id="CadreonReleaseCertification-ExitCriteriaRequirements">Exit Criteria Requirements</h2>'
	certificationPage+='<p>The following exit criteria must be complete before a releaseis considered READY for production</p>'
	certificationPage+='<ul class="ul1"><li>100% of test cases attempted</li>'
	certificationPage+='<li>90% of test cases passed</li><li>No open high severity defects exist</li>'
	certificationPage+='<li>Bug deferral rate less than '+str(acceptableDeferedRate)+'%</li></ul>'
	
	######################################################################################################
	##
	## Jira Ticket Table
	# Jira status: {"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : "grey", "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
	jiraHeaderColor={"New" : "grey", "Ready" : "blue", "In Progress" : "green", "Reopened" : "red", "In Review" : "grey", "Resolved" : "green", "Verified" : "grey", "Closed" : "blue"}
	jiraHeaderName={"New" : "New", "Ready" : "Ready", "In Progress" : "In Dev", "Reopened" : "Reopened", "In Review" : "In Review", "Resolved" : "in QA", "Verified" : "QA Verified", "Closed" : "Closed"}
	
	jiraTableHeader='<div><table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
	jiraTableHeader+='<tr><th class="confluenceTh">Jira Tickets</th>'
	jiraTable=""
	
	
	# Table Definition
	confluenceTableHeader='<div><table><colgroup>'
	confluenceTableHeader+='<col/><col/><col/><col/><col/><col/><col/><col/>'	# Col 1- 8
	confluenceTableHeader+='</colgroup><tbody>'


	#First Header Row
	confluenceTableHeader+='<tr><th> </th>' # Column 1
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" colspan="2" data-highlight-colour="blue" style="text-align: center;">Total Test <p>Execution</p></th>'  # Col 2-3
	confluenceTableHeader+='<th class="highlight-grey confluenceTh" colspan="4" data-highlight-colour="grey" style="text-align: center;">Manual Tests</th>'  			# Col 4-7
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" colspan="5" data-highlight-colour="blue" style="text-align: center;">Automated Tests</th>' 			# Col 8-11
	
	confluenceTableHeader+='</tr>'
	

	# Second Header Row
	confluenceTableHeader+='<tr><th>Sprint</th>' 																		# Column 1
	
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue">Total</th>'			# Column 2
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue"> % </th>'				# Column 3
	confluenceTableHeader+='<th class="highlight-grey confluenceTh" data-highlight-colour="grey">Total</th>'			# Column 4
	confluenceTableHeader+='<th class="highlight-grey confluenceTh" data-highlight-colour="grey"> % </th>'				# Column 5
	confluenceTableHeader+='<th class="highlight-grey confluenceTh" data-highlight-colour="grey">Functional</th>'		# Column 6
	confluenceTableHeader+='<th class="highlight-grey confluenceTh" data-highlight-colour="grey">Regression</th>'		# Column 7
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue">Total Coverage</th>'	# Column 8
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue"> % </th>'				# Column 9
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue">6 mo Av gain</th>'		# Column 10
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue">Total Executed</th>'	# Column 11
	confluenceTableHeader+='<th class="highlight-blue confluenceTh" data-highlight-colour="blue"> % </th>'				# Column 12

	confluenceTableHeader+='</tr>'
	confluenceTableClose='</tbody></table></div>'
	
	######################################################################################################
	##
	## DevOps Table
	
	if (currentSprint % 2 == 0):
		includedSprints="<p>Sprint "+str(previousSprint)+"</p>\n<p>Sprint "+str(currentSprint)+"</p>"
	else:
		includedSprints="Sprint "+str(currentSprint)+"</p>\n<p>Sprint "+str(nextSprint)+"</p>"
	
	devOpsTable='<div><table><colgroup><col/><col/></colgroup><tbody>'				# Two columns
	devOpsTable+='<tr><td>Initiated through ticket</td><td>DEPLOY-{ }</td></tr>' 	# Row #1
	devOpsTable+='<tr><td>Included Sprints</td><td>'+includedSprints+'</td></tr>'	# Row #2
	devOpsTable+='<tr><td>Stage Promotion</td><td> </td></tr>'						# Row #3
	devOpsTable+='<tr><td>Production Promotion</td><td> </td></tr>'					# Row #4
	devOpsTable+='<tr><td>Team</td><td> </td></tr>'									# Row #5
	devOpsTable+='</tbody></table></div>'											# Row #6
	
	
	######################################################################################################
	##
	## Promotion Table
	
	promoTableHeader='<div class="table-wrap"><table class="relative-table wrapped confluenceTable" style="width: 100.0%;">'
	# Define Columns and start table body
	#promoTableHeader+='<colgroup><col style="width: 8.38881%;"/><col style="width: 7.92277%;"/><col style="width: 28.8948%;"/><col style="width: 4.72703%;"/><col style="width: 4.72703%;"/><col style="width: 5.1265%;"/><col style="width: 6.59121%;"/><col style="width: 6.59121%;"/><col style="width: 6.52463%;"/><col style="width: 7.32357%;"/><col style="width: 6.85752%;"/><col style="width: 6.3249%;"/></colgroup><tbody>'
	promoTableHeader+='<colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
	
	# Column Headers
	promoTableHeader+='<tr><td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h2>Component</h2></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><p>QA Lead</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Certified Build and Jenkins Promotion Link</h3></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Stage</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Prod</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><strong>Should Deploy To Support</strong></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h4>Pre and Post Deployment Steps</h4></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Stage</h3><p>Deployment Completed?</p><p>(To Be Filled ByDevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Prod</h3><p>Deployment Completed?</p><p>(To Be Filled By DevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h3>Support</h3><p>Deployment Completed?</p><p>(To Be Filled By DevOps)</p></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" colspan="1" data-highlight-colour="grey"><h4>Production Acceptance Test Confirmation Link</h4></td>'
	promoTableHeader+='<td class="highlight-grey confluenceTd" data-highlight-colour="grey"><h3>Comment</h3></td></tr>'
	
	promoTable=promoTableHeader
	promoTableClose='</tbody></table></div>'
	
	
	# define query to capture total test coverage per project
	total_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE project=%s and sprint_number=%s and sprint_day=%s;")
	auto_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name like '%utom%' and project=%s and sprint_number=%s and sprint_day=%s;")
	autoRegression_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name like '%utomat%' and run_name like '%egress%' and project=%s and sprint_number=%s and sprint_day=%s;")
	manRegression_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name like '%anual%' and run_name like '%egress%' and project=%s and sprint_number=%s and sprint_day=%s;")
	regress_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name like '%egress%' and project=%s and sprint_number=%s and sprint_day=%s;")
	funct_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name like '%Functional%' and project=%s and sprint_number=%s and sprint_day=%s;")
	manual_query= ("SELECT sum(passed), sum(failed), sum(blocked), sum(untested) "
				  "FROM results WHERE run_name not like '%utom%' and project=%s and sprint_number=%s and sprint_day=%s;")
				  
	total_trend_query=("SELECT sprint_number, passed, failed, blocked, untested "
						"FROM results WHERE project=%s and sprint_number>%s and sprint_day=%s order by sprint_number;")
	
	# define query to capture defect reporting
	project_query=('SELECT jira_project FROM projectmapping WHERE project=%s;')
				
	dailyDefects=("SELECT closed_deferred, deferred_count, created_today, critical, major, medium, minor, new_bugs, resolved, in_progress, in_review, verified, reopened, closed"
				   "FROM defects WHERE jira_project=%s and sprint_number=%s and sprint_day=%s ;")
	
	
	print "Current Sprint",currentSprint
	print "Sprint Day #",sprintDay
	
	print
	
	
	productDefects=getProductionDefects()
	prodBugList = {'Total': {'Release':productDefects['total'],'Sprint':0,'Today':0}}
	
	dayOneSinceRelease=datetime.strptime(dayOneForFilter,'%Y-%m-%d')
	dateToday=datetime.strptime(str(date.today()),'%Y-%m-%d')
	dateTomorrow=str(dateToday+timedelta(days=(1))).split()[0]
	firstDayOfSprint=str(dateToday-timedelta(days=(sprintDay))).split()[0]
	
	if (productDefects['total'] == 0):
		prodIssues="No Production Issues"
	
	else:
	
	##################################################
	##
	##        Gather Production Issues
	##
	##################################################
	
	
		for defect in productDefects['issues']:
			thisSprint=0
			todayProdCount=0


			creationDate=defect['fields']['created'].split("T")[0]
			projName=defect['key'].split("-")[0]
			
			defectAge=(dateToday-datetime.strptime(creationDate,'%Y-%m-%d')).days # Determine defect age
			if (defectAge<=2) and ((sprintDay==5) or (sprintDay==0)): defectAge=0  # Include Sat/Sun defects in Monday count
			if (defectAge<=sprintDay):thisSprint=1
			if (defectAge==0):todayProdCount=1
			
			prodBugList['Total']['Sprint']+=thisSprint
			prodBugList['Total']['Today']+=todayProdCount
			
			if not(prodBugList.has_key(projName)):
				prodBugList.update({projName:{'Release':1,'Sprint':thisSprint,'Today':todayProdCount}})
			else:
				prodBugList[projName]['Release']+=1
				prodBugList[projName]['Sprint']+=thisSprint
				prodBugList[projName]['Today']+=todayProdCount
		
		productionDefectFilterString='%20and%20%22Bug%20Type%22%20%3D%20%22Production%20Bug%22%20and%20created%20%3E%3D%20'
		closeFilterString='%20and%20created%20%3C%20'+str(dateTomorrow)
		totalsProductionFilter='<a class="external-link" href="https://projects.mbww.com/issues/?jql=filter%3DProductSet'+productionDefectFilterString
		
		totalsTodayFilter=totalsProductionFilter+str(dateToday).split()[0]+closeFilterString+'" rel="nofollow">'+str(prodBugList['Total']['Today'])+'</a>'
		totalsSprintFilter=totalsProductionFilter+firstDayOfSprint+closeFilterString+'" rel="nofollow">'+str(prodBugList['Total']['Sprint'])+'</a>'
		totalsReleaseFilter=totalsProductionFilter+str(dayOneSinceRelease).split()[0]+closeFilterString+'" rel="nofollow">'+str(prodBugList['Total']['Release'])+'</a>'
		
		prodIssues+="<tr><td>Total</td><td>"+totalsReleaseFilter+"</td><td>"+totalsSprintFilter+"</td><td>"+totalsTodayFilter+"</td></tr>"
		
		for projectName in prodBugList:
			if (projectName is not "Total"):
				prodDefectFilterByProject='<a class="external-link" href="https://projects.mbww.com/issues/?jql=project%3D'+projectName+productionDefectFilterString
				
				todayDefectFilter=prodDefectFilterByProject+str(dateToday).split()[0]+'" rel="nofollow">'+str(prodBugList[projectName]['Today'])+'</a>'
				sprintDefectFilter=prodDefectFilterByProject+firstDayOfSprint+'" rel="nofollow">'+str(prodBugList[projectName]['Sprint'])+'</a>'
				releaseDefectFilter=prodDefectFilterByProject+str(dayOneSinceRelease).split()[0]+'" rel="nofollow">'+str(prodBugList[projectName]['Release'])+'</a>'
				
				prodIssues+="<tr><td>"+projectName+"</td><td>"+releaseDefectFilter+"</td><td>"+sprintDefectFilter+"</td><td>"+todayDefectFilter+"</td></tr>"
			print projectName," This Release: ",prodBugList[projectName]['Release']," This Sprint: ",prodBugList[projectName]['Sprint']," Today: ",prodBugList[projectName]['Today']
		prodIssues+='</tbody></table></div>'	# Close the Table
	
	confluenceBody+=prodIssues
	print
	
	# Get the list of all projects in TestRail
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	
	# Parse each project to determine if it has a current milestone associated
	for project in testRailProjects:
		
		projectID = str(project['id'])
		
		if (projectID != "27"):
		
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			
			for currentMilestone in projectMilestones:
				# If the milestone is current - then review the test runs associated to the milestone
				if (currentMilestone['name'].find(sprintName) > -1):
					# Project has milestone defined, determine the total test cases for the project

					total_data=(project['name'],currentSprint,sprintDay)
					total_trend_data=(project['name'],currentSprint-4,sprintDay)
					
					print project['name']
					
					projectTable=confluenceTableHeader
					
					offset=0
					totalTrend=0.00
					trendCount=0
					currentPercent=None
					certified=True
					
					totalVariance=[]
					pastVariance=[]
					projectStyle=black
					
					## Number of Sprints shown is limited by the offset
					## Standard offset=4
					while (offset<13):

						############################################################################################################
						# getTestCoverage returns values in the following format:
						# {"passed":{"today":0, "yesterday":0, "trend":0},
						#  "failed":{"today":0, "yesterday":0, "trend":0},
						#  "total":{"today":0, "yesterday":0, "trend":0}}
						#  yesterday=previous day's count
						#  trend = previous Sprint count on the same Sprint day
						
						# Functional Test Execution
						functionalCoverage=getTestCoverage(funct_query,project['name'],currentSprint-offset,sprintDay)
						
						# Regression Test Execution
						regressionCoverage=getTestCoverage(regress_query,project['name'],currentSprint-offset,sprintDay)
						
						# Automated Regression Test Execution
						automatedRegression=getTestCoverage(autoRegression_query,project['name'],currentSprint-offset,sprintDay)
						
						# Total Test Coverage
						totalTestCoverage=getTestCoverage(total_query,project['name'],currentSprint-offset,sprintDay)						
						
						# Automated Coverage
						automatedCoverage=getTestCoverage(auto_query,project['name'],currentSprint-offset,sprintDay)
						
						
						#######################################################################################################
						# Determine specific values, based on the queries
						# 
						
						# Manual Tests calculated from Total tests - Automated tests
						totalManualTests=totalTestCoverage['total']['today']-automatedCoverage['total']['today']
						totalManualExecuted=totalTestCoverage['executed']['today']-automatedCoverage['executed']['today']
						totalManualExecutedYesterday=totalTestCoverage['executed']['yesterday']-automatedCoverage['executed']['yesterday']
						totalTests=totalTestCoverage['total']['today']
						totalExecuted=totalTestCoverage['executed']['today']
						totalPassed=totalTestCoverage['passed']['today']
						
						# Functional Automated tests calculated from automated coverage - automated regression
						functionalAutoTotal=automatedCoverage['total']['today']-automatedRegression['total']['today']
						functionalAutoExecuted=automatedCoverage['executed']['today']-automatedRegression['executed']['today']
						
						# Manual Regression is calculated from Regression - Automated Regression
						manRegressTotal=regressionCoverage['total']['today']-automatedRegression['total']['today']
						manRegressExecuted=regressionCoverage['executed']['today']-automatedRegression['executed']['today']
						manRegressExecutedYesterday=regressionCoverage['executed']['yesterday']-automatedRegression['executed']['yesterday']
						manRegressExecutedDelta=manRegressExecuted-manRegressExecutedYesterday
						
						# Functional Manual Tests calculated from TotalManual Tests - Manual Regression Tests
						functionalManualTotal=totalManualTests-manRegressTotal
						functionalManualExecuted=totalManualExecuted-manRegressExecuted
						functionalManualExecutedYesterday=totalManualExecutedYesterday-manRegressExecutedYesterday
						functionalManualExecutedDelta=functionalManualExecuted-functionalManualExecutedYesterday
						
						# Test Execution Difference from previous day
						dailyCreated=totalTestCoverage['total']['today']-totalTestCoverage['total']['yesterday']
						
						autoRegressExecuted=automatedRegression['executed']['today']
						autoRegressTotal=automatedRegression['total']['today']						
						
						totalAutoExecuted=automatedRegression['executed']['today']
						totalAutoTests=automatedRegression['total']['today']
						
						# 6 Month Average improvement in automated coverage
						coverageSixMonthsAgo=float(0.00)
						if (totalTestCoverage['total']['sixMonth'] >0):
							coverageSixMonthsAgo=float(automatedCoverage['total']['sixMonth']/totalTestCoverage['total']['sixMonth'])
						
						coverageToday=float(0.00)
						if (totalTestCoverage['total']['today'] >0):
							coverageToday=float(automatedCoverage['total']['today']/totalTestCoverage['total']['today'])
							
						sixMonthAverageGain=float((coverageToday-coverageSixMonthsAgo)/6)
						
						#Get the Jira Project name 
						
						projQuery="SELECT jira_project FROM projectmapping WHERE project='"+project['name']+"';"

						subCursor.execute(projQuery, (project['name']))
						for (jira_project) in subCursor:
							
							jirProj=jira_project[0]
							projectCertified=True
							dailyDefects=("SELECT production, closed_deferred, deferred_count, created_today, critical, major, closed FROM defects WHERE jira_project='"+jirProj+"' and sprint_number=%s and sprint_day=%s ;")
							
							created_today=0
							critical=0
							major=0
							deferred_count=0
							closed_deferred=0
							
							if (totalTests>0):
								
								###
								## Build the rows for the Certification page
								###
								
								if (offset <1 ):
									# Get defect stats from Jira
									openedBugs=getOpenedBugsCount(jirProj)
									resolvedNonBacklog=getResolvedBugsNotFromBacklog(jirProj)
									allResolved=getAllResolvedBugs(jirProj)
									
									openBugFilter='<a class="external-link" href="https://projects.mbww.com/issues/?jql=project%3D'+jirProj+'%20and%20issuetype%3Dbug%20and%20%22Bug%20Type%22%20!%3D%20%22Production%20Bug%22%20and%20created%20%3E%3D%20'+dayOneForFilter+'" rel="nofollow">'+str(openedBugs)+'</a>'
									resolvedNoBacklogFilter='<a class="external-link" href="https://projects.mbww.com/issues/?jql=project%3D'+jirProj+'%20and%20issuetype%3Dbug%20and%20%22Bug%20Type%22%20!%3D%20%22Production%20Bug%22%20and%20created%20%3E%3D%20'+dayOneForFilter+'%20and%20resolved%20%3E%3D%20'+dayOneForFilter+'" rel="nofollow">'+str(resolvedNonBacklog)+'</a>'
									allResolvedFilter='<a class="external-link" href="https://projects.mbww.com/issues/?jql=project%20%3D%20'+jirProj+'%20AND%20issuetype%20%3D%20Bug%20and%20%22Bug%20Type%22%20!%3D%20%22Production%20Bug%22%20and%20resolved%20%3E%3D%20'+dayOneForFilter+'" rel="nofollow">'+str(allResolved)+'</a>'
									
									deploymentKey=""
									
									if (openedBugs > 0):
										if ((float(openedBugs-allResolved)/float(openedBugs)) > acceptableDeferedRate) : projectCertified=False

									if (totalTests>totalExecuted) : 
										projectCertified=False
										
									if (totalExecuted > 0):
										if (float(totalPassed)/float(totalExecuted) < .9) : projectCertified=False
									if ((critical+major)>0) : projectCertified=False
									
									certProject=project['name']
									# cert row Columns 1-6
									if (totalExecuted > 0):
										certTable+='<tr><td>'+certProject+'</td><td>'+str(totalTests)+'</td><td>'+str(totalExecuted)+'</td><td>'+'{:.2%}'.format(float(totalExecuted)/float(totalTests))+'</td><td>'+str(totalTests)+'</td><td>'+'{:.2%}'.format(float(totalPassed)/float(totalTests))+'</td>'
									else:
										certTable+='<tr><td>'+certProject+'</td><td>'+str(totalTests)+'</td><td> 0 </td><td>0.00%</td><td>'+str(totalPassed)+'</td><td> 0.00% </td>'
									
									# cert row Columns 7
									certTable+='<td>'+str(critical+major)+'</td>'
									
									# cert row 8-10 - Rows with project-specific filters
									certTable+='<td>'+openBugFilter+'</td>'
									certTable+='<td>'+resolvedNoBacklogFilter+'</td>'
									certTable+='<td>'+allResolvedFilter+'</td>'
									
									# cert rows Columns 11,12
									if (openedBugs > 0):
										certTable+='<td>'+'{:.2%}'.format(float(openedBugs-resolvedNonBacklog)/float(openedBugs))+'</td><td>'+'{:.2%}'.format(float(openedBugs-allResolved)/float(openedBugs))+'</td>'
									else:
										certTable+='<td>0.00%</td><td>0.00%</td>'
										
									# cert row Columns 13-14
									if (projectCertified) :
										criteria="yes"
										criteriaStyle=green
									else:
										criteria="NO"
										criteriaStyle=red
									certTable+='<td><span style='+criteriaStyle+'>'+criteria+'</span></td><td></td></tr>'
									
									####
									#  Sprint status
									###
									sprintTickets=getSprintTickets(jirProj)
									totalTickets=sprintTickets['total']
									
									columnSequence=["New", "Ready", "In Progress", "Reopened", "In Review", "Resolved", "Verified", "Closed" ]
									storyStatus={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
									storyPoints={"New" : 0.0, "Ready" : 0.0, "In Progress" : 0.0, "Reopened" : 0.0, "In Review" : 0.0, "Resolved" : 0.0, "Verified" : 0.0, "Closed" : 0.0}
									bugStatus={"New":0, "In Progress":0, "In Review":0, "Resolved":0, "Reopened":0, "Verified":0, "Closed":0}
									productionIssues={"New":0, "In Progress":0, "In Review":0, "Resolved":0, "Reopened":0, "Verified":0, "Closed":0}
									totalSprintPoints=0.0
									totalStories=0
									totalBugs=0
									noEstimates=0
									noEstimatePoints=0.0
									noPoints=0
									
									#print jirProj,totalTickets,"Tickets"
									for ticket in sprintTickets['issues']:
									
										ticketKey=ticket['key']
										ticketSummary=ticket['fields']['summary']
										
										ticketDetail=requests.get(ticket['self'], headers=APIHeaders, auth=jiraAuth,timeout=None)
										details=ticketDetail.json()
										
										ticketDueDate=details['fields']['duedate']
										ticketStoryPoints=details['fields']['customfield_10002']
										if (ticketStoryPoints is None) : ticketStoryPoints=0.0
										
										ticketType=details['fields']['issuetype']['name']
										ticketStatus=details['fields']['status']['name']
										
										if (ticketType == "Bug") : 
											totalBugs+=1
											bugStatus[ticketStatus]+=1
											bugType=details['fields']['customfield_12723']
											if (bugType == "Production Bug"):
												productionIssues[ticketStatus]+=1
												print "Production Defect: ",ticketKey
											
										if (ticketType == "Story") : 
											#jiraStatus=details['fields']['status']['name']
											totalStories+=1
											storyStatus[ticketStatus]+=1
											storyPoints[ticketStatus]+=ticketStoryPoints
										
										totalSprintPoints+=ticketStoryPoints
										if ("eployment" not in ticketSummary) and ("eploy" not in ticketSummary):
											if (ticketType=="Story" and ticketStoryPoints <1) : noPoints+=1
											if (ticketType=="Story" and ticketDueDate is None) : 
												noEstimates+=1
												noEstimatePoints+=ticketStoryPoints
												
										else:
											deploymentKey=details['key']
									
									defectStatus=updateDefectTable(projectCursor,str(currentSprint), str(sprintDay), jirProj, bugStatus)
									updateJiraTable(projectCursor,"jirapoints", str(currentSprint), str(sprintDay), jirProj, storyPoints)
									updateJiraTable(projectCursor,"jirastory", str(currentSprint), str(sprintDay), jirProj, storyStatus)
									
									jiraTableHeader='<div><table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody>'
									jiraTableHeader+='<tr><th class="confluenceTh">Jira Tickets</th><th>Total</th>'
									
									jiraPointsRow='<tr><td>Story Points</td><td>'+str(int(totalSprintPoints))+'</td>'
									jiraStoryRow='<tr><td>Story Tickets</td><td>'+str(int(totalStories))+'</td>'
									jiraDefectRow='<tr><td>Defects</td><td>'+str(totalBugs)+'</td>'
									
									#for jValue in storyStatus:
									for jValue in columnSequence:
										jiraTableHeader+='<th class="highlight-'+jiraHeaderColor[jValue]+' confluenceTh" data-highlight-colour="'+jiraHeaderColor[jValue]+'">'+jiraHeaderName[jValue]+'</th>'
										jiraPointsRow+='<td>'+str(int(storyPoints[jValue]))+'</td>'
										jiraStoryRow+='<td>'+str(int(storyStatus[jValue]))+'</td>'
									
										if (jValue in bugStatus) : 
											jiraDefectRow+='<td>'+str(bugStatus[jValue])+'</td>'
										else:
											jiraDefectRow+='<td></td>'
									
									jiraTableHeader+='</tr>'
									jiraPointsRow+='</tr>'
									jiraStoryRow+='</tr>'
									jiraDefectRow+='</tr>'
									
									jiraTableRows=jiraPointsRow+jiraStoryRow+jiraDefectRow+'</tbody></table></div><p></p>'
								
									jiraTable=jiraTableHeader+jiraTableRows
									
									if (deploymentKey != ""):	# If the project has a ticket with the word 'eployment'
										promoRow='<tr><td class="highlight-grey confluenceTd" colspan="2" data-highlight-colour="grey">'
										promoRow+='<h3 id="CertificationPage-'+jirProj+'Trackerkey-'+deploymentKey+'">'+certProject+'</h3></td>'
										## Add link to build promotion
										## promoRow+='<div class="content-wrapper">'
										promoRow+='<td class="highlight-grey confluenceTd" colspan="10" data-highlight-colour="grey">'
										promoRow+='Deployment Ticket: <a class="external-link" href="https://projects.mbww.com/browse/'+deploymentKey+'" rel="nofollow" target="_blank" data-ext-link-init="true">'+deploymentKey+'</a>'
										## promoRow+='</td></div></tr>'
										promoRow+='</td></tr>'
									else:
										promoRow='<tr><td class="highlight-grey confluenceTd" colspan="12" data-highlight-colour="grey">'
										promoRow+='<h3 style="text-align: left;" id="CertificationPage-'+jirProj+'">'+certProject+'</h3></td></tr>'
									
									promoTable+=promoRow			### Commented out for trouble shooting purposes
									
									#################
									##  Add each build component to the promoTable
									
									componentCursor.execute("SELECT component, versionMethod, jenkinsProject FROM componentmapping WHERE project='"+jirProj+"';",)
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
										
										lastSuccessBuild=".?."
										buildLink="n/a"
										if (componentQAPromotion.status_code <300):
											componentInfo=componentQAPromotion.json()
											lastSuccessBuild=componentInfo['id']
											buildLink=componentInfo['url']
										promotionLink="http://jenkins.cadreonint.com/job/"+jenkinsProject+"/"+lastSuccessBuild+"/promotion/"
										
										promoRow='<tr><td>'+component+'</td>'
										promoRow+='<td></td><td><a class="external-link" href="'+promotionLink+'" rel="nofollow">Build '+lastSuccessBuild+'</a></td>'
										promoRow+='<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'
										promoTable+=promoRow
									
									## What did QA do today?
									headerSpan=0
									dailyQAStatus='<div><table><colgroup><col/><col/>'

									dailyDefectHeader='<tr><th class="confluenceTh">Tests Created</th><th class="confluenceTh">Manual Tests Executed</th>'
									dailyDefectRow='<tr><td>'+str(dailyCreated)+'</td><td>'+str(totalManualExecutedYesterday)+'</td>'
									
									for defectValue in defectStatus:
										if defectValue in ('New', 'Verified','Closed'):
											headerSpan+=1
											dailyQAStatus+='<col/>'
											dailyDefectHeader+='<th class="confluenceTh">'+defectValue+'</th>'
											dailyDefectRow+='<td>'+str(defectStatus[defectValue]['today']-defectStatus[defectValue]['yesterday'])+'</td>'
									
									dailyQAStatus+='</colgroup><tbody><tr><th class="highlight-blue confluenceTh" colspan="2" data-highlight-colour="blue" style="text-align: center;">Test Cases</th><th class="highlight-blue confluenceTh" colspan="'+str(headerSpan)+'" data-highlight-colour="blue" style="text-align: center;">Bug Activity</th></tr>'
									dailyQAStatus+=dailyDefectHeader+'</tr>'+dailyDefectRow+'</tr></tbody></table></div>'
									
								# Column 1 - current Sprint
								confluenceTableRow='<tr><td style=\"text-align: center;\">'+str(currentSprint-offset)+'</td>'
								
								## Total Tests
								# Column 2 - total Executed tests / total Tests
								if (totalTests >0):
									confluenceTableRow+='<td>'+str(totalExecuted)+' / '+str(totalTests)+'</td>'
								else:
									confluenceTableRow+='<td> 0 / 0 </td>'
								
								# Column 3 - total executed as percentage
								confluenceTableRow+='<td>'+'{:.2%}'.format(float(totalExecuted)/float(totalTests))+'</td>'
								
								## Manual Tests
								# Column 4 - total manual executed / total
								confluenceTableRow+='<td>'+str(totalManualExecuted)+' / '+str(totalManualTests)+'</td>'
								
								# Column 5 - percentage
								if (totalManualTests > 0):
									confluenceTableRow+='<td>'+'{:.2%}'.format(float(totalManualExecuted)/float(totalManualTests))+'</td>'								
								else: 
									confluenceTableRow+='<td>0.00%</td>'
								
								# Column 6 - Total Manual Functional Tests Executed
								confluenceTableRow+='<td>'+str(functionalManualExecuted)+' / '+str(functionalManualTotal)+'</td>'
								
								# Column 7 - Total Manual Regression Tests Executed
								confluenceTableRow+='<td>'+str(manRegressExecuted)+' / '+str(manRegressTotal)+'</td>'
								
								## Automated Tests
								# Column 8 - automated / total
								confluenceTableRow+='<td>'+str(totalAutoTests)+' / '+str(totalTests)+'</td>'
								
								# Column 9 - percentage
								if (totalAutoTests > 0):
									confluenceTableRow+='<td>'+'{:.2%}'.format(float(totalAutoTests)/float(totalTests))+'</td>'	
								else: 
									confluenceTableRow+='<td>0.00%</td>'
								
								## Automated Coverage Improvement
								# Column 10 - 6 Month Average Improvement
								
								#if (sixMonthTotalCoverage > 0):
								confluenceTableRow+='<td style=\"text-align: center;\">'+'{:.2%}'.format(float(sixMonthAverageGain))+'</td>'
								#else: 
								#	confluenceTableRow+='<td>0.00%</td>'

								## Regression Tests
								# Column 11 - Automated Execution

								confluenceTableRow+='<td style=\"text-align: center;\">'+str(totalAutoExecuted)+' / '+str(totalAutoTests)+'</td>'
								

								# Column 12 - Automated Regression %
								#autoStyle=black
								if (autoRegressTotal>0):
									
									regressionPercentage=(float(totalAutoExecuted)/float(totalAutoTests))
									autoStyle=severityColor(regressionPercentage,"black")
									if (regressionPercentage<1):
										confluenceTableRow+='<td><span style='+autoStyle+'><bold>'+'{:.2%}'.format(float(totalAutoExecuted)/float(totalAutoTests))+'</bold></span></td>'
									else:
										confluenceTableRow+='<td><span style='+autoStyle+'>'+'{:.2%}'.format(float(totalAutoExecuted)/float(totalAutoTests))+'</span></td>'
								else:
									confluenceTableRow+='<td>0.00%</td>'
								
								confluenceTableRow+='</tr>'

								projectTable+=confluenceTableRow
								
						offset+=1
					## perform statistics per project
					if(trendCount>1):

						modelAverage=totalTrend/float(trendCount)
						
						if (currentPercent != None):
							deviation=currentPercent-modelAverage
							projectVariance='Current Sprint: '+'{:.2%}'.format(currentPercent)+"  Model: "+'{:.2%}'.format(modelAverage)
						else:
							deviation=0.00
							projectVariance='Current Sprint: undefined  Model: '+'{:.2%}'.format(modelAverage)
						projectStyle=green
						if (deviation<0):
							projectStyle=yellow
							if (sprintDay>7):
								projectStyle=red
						
						if (deviation<-0.2):
							projectStyle=red
							if (sprintDay<3):
								projectStyle=yellow

						
					else:
						#projectVariance='<em>Insufficient trend data to establish model</em>'
						projectVariance='<em>trend data</em>'
						projectStyle=yellow
						
					projectTable+=confluenceTableClose
					
					# Add Jira Table to the content
					if (int(sprintDay) > 0):
						confluenceBody+='<p><h3><span style='+projectStyle+'><strong>'+project['name']+'</strong></span></h3></p><p>'+dailyQAStatus+'</p>'+jiraTable+projectTable
					else:
						confluenceBody+='<p><h3><span style='+projectStyle+'><strong>'+project['name']+'</strong></span></h3></p><p>'+'Sprint Planning'+'</p>'+jiraTable+projectTable
					print
					
					#print "Sprint ",str(currentSprint)," breakdown: "
					#print "Total Tests: ",totalTestCoverage
					#print "Functional Tests: ",functionalCoverage
					#print "Automated Tests: ",automatedCoverage
					#print "Regression Tests: ",regressionCoverage
					#print "Automated Regression: ",automatedRegression
					
	projectCursor.close()
	componentCursor.close()
	cursor.close()
	subCursor.close()
	functTestCursor.close()
	autoRegres.close()
	autoCursor.close()
	pythonCursor.close()
	db.close()
	
	certTable+='</tbody></table></div>'
	#print certTable
	promoTable+=promoTableClose
	
	#sys.exit()
	
	confluenceGet=requests.get("https://wiki.mbww.com/rest/api/content?title=Coverage+for+Current+Sprint+Day&expand=body.view,version,extensions.ancestors", headers={'Content-Type': 'application/json'}, auth=jiraAuth)

	if (confluenceGet.status_code>399):
		print confluenceGet.raise_for_status()
		
	confluenceContent=confluenceGet.json()
	confluenceContentId=confluenceContent['results'][0]['id']
	pageVersion=confluenceContent['results'][0]['version']['number']
	contentPath=confluenceContent['results'][0]['version']['_expandable']['content']
	confluencePageTitle=confluenceContent['results'][0]['title']
	
	updatedVersion=pageVersion+1
	
	dailyPlusCert=confluenceBody+certTable+promoTable
	certificationPage+=certTable+promoTable
	#dailyPlusCert=confluenceBody+certTable+devOpsTable+promoTable
	
	confluencePutBody = json.dumps({u"version": {u"number": updatedVersion},u"title": confluencePageTitle,u"type": u"page",u"body": {u"storage": {u"value": dailyPlusCert,u"representation": u"storage"}}})

	#print promoTable	
		
	confluenceUpdate=requests.put("https://wiki.mbww.com"+contentPath,data=confluencePutBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth)

	# We like to print errors when the update fails
	if (confluenceUpdate.status_code > 399):
		print jiraAuth
		print confluencePutBody
		print confluenceUpdate.raise_for_status()

	
	sprintDayGet=requests.get("https://wiki.mbww.com/rest/api/content?title=Sprint+Day+%23"+str(sprintDay+1)+"+%7C+Test+case+coverage&expand=body.view,version,extensions.ancestors", headers={'Content-Type': 'application/json'}, auth=jiraAuth)
	sprintDayContent=sprintDayGet.json()
	sprintDayContentId=sprintDayContent['results'][0]['id']
	sprintDayPageVersion=sprintDayContent['results'][0]['version']['number']
	sprintDayPath=sprintDayContent['results'][0]['version']['_expandable']['content']
	sprintDayTitle=sprintDayContent['results'][0]['title']
	sprintDayVersionUpdate=sprintDayPageVersion+1

	sprintDayPutBody=json.dumps({u"version": {u"number": sprintDayVersionUpdate},u"title": sprintDayTitle,u"type": u"page",u"body": {u"storage": {u"value": confluenceBody,u"representation": u"storage"}}})
	sprintDayUpdate=requests.put("https://wiki.mbww.com"+sprintDayPath,data=sprintDayPutBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth)
	
	# pass in the value certPage=PAGENAME_HERE
	certificationPageTitle=getCertificationPage()
	if (certificationPageTitle!=False) :
	
		certpage=requests.get("https://wiki.mbww.com/rest/api/content?title="+certificationPageTitle+"&expand=body.view,version,extensions.ancestors", headers={'Content-Type': 'application/json'}, auth=jiraAuth)
		certpageContent=certpage.json()
		certpageContentId=certpageContent['results'][0]['id']
		certpageVersion=certpageContent['results'][0]['version']['number']
		certpagePath=certpageContent['results'][0]['version']['_expandable']['content']
		certpageTitle=certpageContent['results'][0]['title']
		certpageVersion=certpageVersion+1
		certpageBody=json.dumps({u"version": {u"number": certpageVersion},u"title": certpageTitle,u"type": u"page",u"body": {u"storage": {u"value": certificationPage,u"representation": u"storage"}}})
		
		certpageUpdate=requests.put("https://wiki.mbww.com"+certpagePath,data=certpageBody, headers={'Content-Type': 'application/json'}, auth=jiraAuth)
		
		#certPage=Cadreon+Release+2.20+Certification
	
if __name__ == '__main__':
    main()