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

## Global values
# sprintEpoch=18, the first sprint of 2016
# Epoch 01/04/2016 = day 1 of sprint 18
# Epoch and sprint start dates should be updated, if we modify our Sprint schedule.

sprintEpoch=18
cadreonEpoch=date(2016,1,4)

def determineSprintDay(today):
	#today=date.today()
	daysSinceEpoch=(today-cadreonEpoch).days

	sprintStart=(currentSprint-sprintEpoch)*14
	
	sprintDay=daysSinceEpoch-sprintStart
	if (sprintDay>4):
		sprintDay-=2
	
	return (sprintDay)
	
	
def main():
	# capture script input options, for future use
	cmdOptions = sys.argv
	
	# Connect to coverage database
	db=mysql.connector.connect(user='admin', password='admin',host='127.0.0.1',database='coverage')
	cursor=db.cursor()
	
	# define insert query for test coverage results
	add_result = ("INSERT INTO results "
               "(sprint_number, sprint_day, project, run_name, passed, failed, blocked, untested) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
	
	day=0
	today=date.today()
	daysSinceEpoch=(today-cadreonEpoch).days

	while (day<daysSinceEpoch):
		nextDay=cadreonEpoch+timedelta(day)
		if (timedelta(days=nextDay.weekday()).days <5):
			reportDate=nextDay.strftime("%Y-%m-%d")
			reportString = "http://ec2-54-210-184-26.compute-1.amazonaws.com/TestRailResults." + reportDate + ".txt"
			reportRequest=requests.get(reportString)
			testReport=reportRequest.content.split('\n')
			
			sprintNumber=testReport[2].split(":")[1].split('t ')[1].strip()
			if (int(sprintNumber)>17):
				sprintStart=(int(sprintNumber)-sprintEpoch)*14
		
				sprintDay=day-sprintStart
				if (sprintDay>4):
					sprintDay-=2
				
				totalColumn=testReport[5].find("TOTAL")
				untestedColumn=testReport[5].find("UNTESTED")
				passedColumn=testReport[5].find("PASSED")
				failedColumn=testReport[5].find("FAILED")
				blockedColumn=testReport[5].find("BLOCKED")
				retestColumn=testReport[5].find("RETEST")
				progressColumn=testReport[5].find("IN-PROGRESS")
				lateColumn=testReport[5].find("UNTESTED-LATE")
				untestedColumn=testReport[5].find("UNTESTED")
				
				project="UNDEFINED"
				
				testReport.remove(testReport[0])
				testReport.remove(testReport[0])
				testReport.remove(testReport[0])
				testReport.remove(testReport[0])
				
				for line in testReport:
					description=line[0:totalColumn]
					total=line[totalColumn:].split('(')[0].strip()
					untested=line[untestedColumn:].split('(')[0].strip()
					passed=line[passedColumn:].split('(')[0].strip()
					failed=line[failedColumn:].split('(')[0].strip()
					blocked=line[blockedColumn:].split('(')[0].strip()
					retest=line[retestColumn:].split('(')[0].strip()
					lateUntested=line[lateColumn:].split('(')[0].strip()
					
					if (total.find("TOTAL")>-1):
						project=description
					elif(len(total)>0) and not(line.find("#")>-1):
						
						#print "Sprint Number: ",sprintNumber,"Sprint Day: ",sprintDay," Project: ",project," Run: ",description," Passed: ",passed," Failed: ",failed," Blocked: ",blocked," Untested: ",untested
						print ".",
						#updateDatabase:			
						data_result=(sprintNumber, sprintDay, project, description, passed, failed, blocked, untested)
						cursor.execute(add_result, data_result)
						db.commit()
		day+=1
		
		#if(day>40):
		#	day+=300
						
	
	cursor.close()
	db.close()
	
if __name__ == '__main__':
    main()