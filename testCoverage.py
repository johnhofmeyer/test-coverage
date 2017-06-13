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
import codecs
import base64

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date
from sys import exit
from codecs import decode

## Global values
# sprintEpoch=18, the first sprint of 2016
# Epoch 01/04/2016 = day 1 of sprint 18
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

sprintEpoch=18
cadreonEpoch=date(2016,1,4)
APIHeaders={'Content-Type': 'application/json'}

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

def getNetworkAuth():
	theNumber='9'
	unWord='54mzpbTE'
	theWord=decode("theWord",unWord)
	return theNumber+theWord+theNumber
	
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

def isOldDate(theWord):

	if (len(theWord)>5):
		try:
			theDate=datetime.strptime(theWord,'%m/%d/%Y')
			today=date.today()
			if (theDate.day == today.day) and (theDate.month == today.month) and (theDate.year == today.year):
				return False
			else: 
				return True
		except:
			return False
	return False
			
def excludeRun(runName):
	notDates=["sprint","automated","manual","regression","functional","ui","api","test","tests","run"]
	containsOldDate=False

	splitName=runName.split()
	for splitWord in splitName:
		if (splitWord.lower() not in notDates): # only check words that may contain date information
			if (isOldDate(splitWord)): containsOldDate=True
	return containsOldDate

def parseJiraBugs(issueList):
	jiraBugCount=0
	bugList="No Bugs"
	try:
		for issue in issueList:
			issueName=issue['inwardIssue']['fields']['issuetype']['name']
			if (issueName=="Bug"): 
				bugSummary=issue['inwardIssue']['fields']['summary']
				jiraBugCount+=1
				if (bugList=="No Bugs"):
					bugList='\t'+str(issue['inwardIssue']['key']+": "+bugSummary)
				else:
					bugList+=chr(13)+'\t'+str(issue['inwardIssue']['key']+": "+bugSummary)
		
		if (jiraBugCount==1):
			return("1 associated bug"+chr(13)+bugList+chr(13))
		if (jiraBugCount>1):
			return(str(jiraBugCount)+" associated bugs"+chr(13)+bugList+chr(13))
	except:
		pass
		#return(chr(13)+bugList+chr(13))
		
	return(chr(13)+bugList+chr(13))
	
def logAndPrint(theLog,message):
	theLog.writelines(message+chr(13))
	printOut=message.split(chr(13))
	for lineOut in printOut:
		print lineOut+'\r\n'
	#print message
	
	
	return
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	sep=chr(47)
	
	fileName="C:"+sep+"Users"+sep+"John.Hofmeyer"+sep+"Desktop"+sep+"testCoverage.txt"
	fo=open(fileName,'w')
	
	jiraAuth=HTTPBasicAuth('john.hofmeyer@cadreon.com',getNetworkAuth())
	
	# Connect to coverage database
	db=mysql.connector.connect(user='daily_stats', password='yVgvQM7NU&vJXj6637D9',host='qa-daily-stats.ckvgpujcycok.us-east-1.rds.amazonaws.com',database='coverage',buffered=True)

	cursor=db.cursor()
	
	# define queries for test coverage results
	count_query= ("SELECT Count(*) from results WHERE sprint_number = %s and sprint_day = %s and project = %s and run_name = %s ;")
	# count data = sprint_number, sprint_day, project, run_name
	
	# both the INSERT and UPDATE queries use the same data set
	# data=passed, failed, blocked, untested, sprint_number, sprint_day, project, run_name
	
	insert_result=("INSERT INTO results "
               "(passed, failed, blocked, untested, sprint_number, sprint_day, project, run_name) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
			   
	update_result=("UPDATE results "
				   "SET passed = %s , failed = %s , blocked = %s , untested = %s"
				   "WHERE sprint_number = %s AND sprint_day = %s AND project= %s AND run_name = %s"
				   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
	
	
	# Determine current sprint number, current Sprint day, and first day of Sprint 
	currentSprint=determineSprintNumber()
	sprintName="Sprint "+str(currentSprint)
	sprintDay=determineSprintDay()
	
	# Determine the first day of the sprint
	sprintFirstDay=str(cadreonEpoch+timedelta(days=(currentSprint-sprintEpoch)*14-1)) # Technically, this is the Sunday before the Sprint begins
	firstDayUnix=datetime.today()-timedelta(days=sprintDay)
	if (sprintDay>5):
		firstDayUnix=(datetime.today()-timedelta(days=sprintDay+2))
	firstDayUnix=str(int((firstDayUnix-datetime(1970, 1, 1)).total_seconds()))
	
	msg= "Current Sprint"+str(currentSprint)
	logAndPrint(fo,msg)
	msg= "Sprint Day #"+str(sprintDay)
	logAndPrint(fo,msg)

	
	# Get the list of all projects in TestRail
	projects=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_projects', headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
	testRailProjects=projects.json()
	
	################
	##
	##  Define dictionaries for test cases
	projectJiraDict={}
	allTestCases=[]
	
	resultText={'1':'passed','2':'blocked','3':'untested','4':'Retest','5':'Failed','6':'In Progress','7':'Untested-Late','8':'Untested n/a'}
	
	
	# Parse each project to determine if it has a current milestone associated
	
	############################################################
	##
	##  Main loop - cycle through each project in Testrail
	##
	
	for project in testRailProjects:
		
		projectID = str(project['id'])
		
		###################################################################
		##
		##	Exclude Test Projects
		##
		
		if (str(projectID) not in ("17", "26", "27", "29") ):
		
			milestones=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_milestones/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectMilestones=milestones.json()
			mstoneId=-1
			mstoneName="undefined"
			
			#################################################################
			##
			##  Determine total tests created, since first day of the Sprint
			##
			
			newTests=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_cases/'+projectID+"&created_after="+str(firstDayUnix), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
			projectTests=newTests.json()
			#print "Project ID: ",projectID
			for testCase in projectTests:

				if (testCase['milestone_id'] != mstoneId):
					mstoneName="undefined"
					for mValue in projectMilestones:
						if (mValue['id']==testCase['milestone_id']):
							mstoneName=mValue['name']
					allTestCases.append(testCase['id'])
			
				# Determine if the test case is assigned to a Jira ticket, if not assign it to 'unknown'
				if (testCase['refs'] is None): 
					jiraTicket=['unknown']
				else:
					jiraTicket=testCase['refs'].split(",")
				
				#print type(jiraTicket)
				
				if projectJiraDict.has_key(projectID):
					for jiratx in jiraTicket:
						jtx=jiratx.strip()
						if projectJiraDict[projectID].has_key(jtx):
							testCaseList=projectJiraDict[projectID][jtx]
							testCaseList.append({'testcaseID':testCase['id'],'title':testCase['title'],'milestone':mstoneName,'result':'untested'})
							projectJiraDict[projectID][jtx]=testCaseList
						else:
							projectJiraDict[projectID].update({jtx:[{'testcaseID':testCase['id'],'title':testCase['title'],'milestone':mstoneName,'result':'untested'}]})
				else:
					for jiratx in jiraTicket:
						jtx=jiratx.strip()
						projectJiraDict.update({projectID:{jtx:[{'testcaseID':testCase['id'],'title':testCase['title'],'milestone':mstoneName,'result':'untested'}]}})
				#print testCase['id']
				
				
			
			
			for currentMilestone in projectMilestones:
				# If the milestone is current - then review the test runs associated to the milestone
				if (currentMilestone['name'].find(sprintName) > -1):
				
					milestoneID=currentMilestone['id']
					runs=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_runs/'+projectID, headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
					projectRuns=runs.json()
					
					logAndPrint(fo," ")
					logAndPrint(fo,"#############################################################################")
					msg= "## Project: "+project['name']#," Milestone: ",currentMilestone['name']
					logAndPrint(fo,msg)
					logAndPrint(fo,"#############################################################################")
					
					for run in projectRuns:
						
						excludeWords=["production","prod","staging","stage"]
						if (run['milestone_id'] == currentMilestone['id']) and (run['name'].find("Production Verification") <0) and (run['name'].find("Staging Verification") < 0) and (excludeRun(run['name']) == False):

							if (run['name'].find("egression")<0):
								#testsInRun=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_tests/'+str(run['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
								runResults=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_results_for_run/'+str(run['id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
								
								testList=runResults.json()
								#print allTestCases
								for test in testList:

									testsInRun=requests.get('https://testrail.cadreon.com/testrail/index.php?/api/v2/get_test/'+str(test['test_id']), headers={'Content-Type': 'application/json'}, auth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123'))
									tc=testsInRun.json()['case_id']
									#print tc,
									if (tc in allTestCases):
										#print "Test case match: ",
										#print test['test_id'], tc ,resultText[str(test['status_id'])]
										for projectJira in projectJiraDict[projectID]:
											for testListResult in projectJiraDict[projectID][projectJira]:
												#print testListResult
												if (tc==testListResult['testcaseID']):
										
													updatedResult=testListResult

													if (test['status_id'] is None):
														updatedResult['result']="None"
													else:
														updatedResult['result']=resultText[str(test['status_id'])]
													
													projectJiraDict[projectID][projectJira].remove(testListResult)
													projectJiraDict[projectID][projectJira].append(updatedResult)
						
							count_data=(currentSprint, sprintDay, project['name'], run['name'])
							query_data=(run['passed_count'], run['failed_count'], run['blocked_count'], run['untested_count'], currentSprint, sprintDay, project['name'], run['name'])

							cursor.execute(count_query,count_data)
							
							for rowCount in cursor:
								resultCount=rowCount[0]

							if (resultCount>0):
								# UPDATE
								cursor.execute("UPDATE results "
											   "SET passed = "+str(run['passed_count'])+" , failed = "+str(run['failed_count'])+" , blocked = "+str(run['blocked_count'])+" , untested = "+str(run['untested_count'])+""
											   "WHERE sprint_number = "+str(currentSprint)+" AND sprint_day = "+str(sprintDay)+" AND project= "+(project['name'])+" AND run_name = "+run['name']+"",
											   "VALUES (%s)",str(run['passed_count']))

							else:
								# INSERT
								cursor.execute(insert_result, query_data)
							db.commit()
							
							msg= run['name']+ "\tPassed:\t"+str(run['passed_count'])+"\tFailed:\t"+str(run['failed_count'])+"\tBlocked:\t"+str(run['blocked_count'])+"\tUntested:\t"+str(run['untested_count'])
							logAndPrint(fo,msg)
							
					logAndPrint(fo," ")
	
			# Some projects do not have new tests, exclude them from printing
			if projectJiraDict.has_key(projectID):

				for jirt in projectJiraDict[projectID]:
					
					if (jirt != 'unknown'):
						ticketDetail=requests.get("https://projects.mbww.com/rest/api/2/issue/"+jirt, headers=APIHeaders, auth=jiraAuth,timeout=None)
						details=ticketDetail.json()
						
						## Test case descriptions are not always in UTF8 format...
						try:
							if (details['fields']['duedate']==None):
								dueDate="None"
							else:
								try:
									dueDate=details['fields']['duedate'].encode('UTF-8')
								except:
									pass
						except:
							print "exception in jira ticket format"
						
						try:
							issueType=details['fields']['issuetype']['name'].encode('UTF-8')
						except:
							issueType="unknown"
						
						try: 
							if (type(details['fields']['issuetype']['description'])==None):
								issueDescription=""
							else:
								try:
									issueDescription=details['fields']['description'].encode('UTF-8')
								except:
									issueDescription="unknown"
						except:
							print "exception in Json object"
							print details
						try:
							issueStatus=details['fields']['status']['statusCategory']['name'].encode('UTF-8')
						except:
							issueStatus="unknown"
						
						logAndPrint(fo,"- - - - - - - - - - - - - - - - - - - - - - -")
						msg=jirt #+": "+issueDescription
						logAndPrint(fo,msg)
						
						msg= "Due Date:"+str(dueDate)
						logAndPrint(fo,msg)
						msg= "Issue Type:"+issueType
						logAndPrint(fo,msg)

						#print "Description:",issueDescription
						msg= "Status:"+issueStatus
						logAndPrint(fo,msg)
						
						
						####################
						## Issues related to the Jira Ticket
						
						#details['fields']['issuelinks']
						try:
							logAndPrint(fo,parseJiraBugs(details['fields']['issuelinks']))
						except:
							print details
						
						###################
						## Test Cases related to the Jira Ticket
						msg= "Test Cases:"+str(len(projectJiraDict[projectID][jirt]))
						logAndPrint(fo,msg)

						for jiraTestCase in projectJiraDict[projectID][jirt]:
							try:
								msg= '  '+jiraTestCase['result']+' '+str(jiraTestCase['testcaseID'])+' '+jiraTestCase['title']
								logAndPrint(fo,msg)
							except:
								print "\texception in test case coverage"
								try:
									print "\ttest case:",str(jiraTestCase['testcaseID'])
								except:
									print "\t** issue in test case ID **"
								try: 
									print "\ttest status:",str(jiraTestCase['result'])
								except:
									print "\t** issue in test result **"
						print
					else:
						print "The following tests do not have a Jira ticket assigned to them in Testrail"
						for jiraTestCase in projectJiraDict[projectID]['unknown']:
							try:
								msg= '  '+' '+str(jiraTestCase['result'].encode('UTF-8'))+' '+str(jiraTestCase['testcaseID'])+' '+jiraTestCase['title'].encode('UTF-8')
								logAndPrint(fo,msg)
							except:
								try:
									print jiraTestCase
									print str(jiraTestCase['testcaseID'])
									
								except:
									print "UPDATE TESTRAIL"
						print
						
				logAndPrint(fo,"- - - - - - - - - - - - - - - - - - - - - - -")
					
	cursor.close()
	db.close()

	msg= "total new test cases this sprint: "+str(len(allTestCases))
	logAndPrint(fo,msg)

	fo.close()		
			
if __name__ == '__main__':
    main()