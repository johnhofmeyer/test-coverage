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

from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, date

testrailAuth=HTTPBasicAuth('testrail.automation@cadreon.com','cadreon123')
APIHeaders={'Content-Type': 'application/json'}


def main():
	# capture script input options, for future use
	cmdOptions = sys.argv

	testcaseId='705293'
	
	testrailAPIHost="https://testrail.cadreon.com/testrail.index.php?/api/v2"
	
	testcase=requests.get(testrailAPIHost+"/get_case/"+testcaseId, headers=APIHeaders, auth=testrailAuth)
	
	testinfo=testcase.json()
	print testinfo





if __name__ == '__main__':
    main()