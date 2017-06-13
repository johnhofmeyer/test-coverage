from datetime import datetime, timedelta, date
sprintEpoch=18
cadreonEpoch=date(2016,1,4) #Day 1 of Sprint 18

'''
sprintEpoch=57
cadreonEpoch=date(2017,7,10) #Day 1 of Sprint 57
'''

def determineSprintNumber():
	today=date.today()
		
	thisMonday=today-timedelta(days=today.weekday()) # discard the remainder in the next calculation
	
	sprintsSinceEpoch=((thisMonday-cadreonEpoch).days)/14
	
	currentSprint=sprintEpoch+sprintsSinceEpoch

	return(currentSprint)

def main():
	print determineSprintNumber()

if __name__ == '__main__':
    main()