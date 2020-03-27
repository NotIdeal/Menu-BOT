import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("botmenu.json", scope)


client = gspread.authorize(creds)

meal = client.open("meals").sheet1


def get_type(typee):
	''' to get type of meal 
	there are four type of meal:
	'meal' , 'sweet' , 'drink' , 'all'
	other arguments will return EROR
	'''

	global meal 

	result = []
	current = [''] * 2
	column1 = meal.col_values(1)
	column2 = meal.col_values(2)
	column3 = meal.col_values(3)
	
	j = min(len(column1),len(column2),len(column3))
	
	for i in range(1,j):
		if typee == 'all':
			current[0] = column1[i]
			current[1] = int(column2[i])
			result.append(current)
		current = ['','']

		if 	column3[i] == typee:
			current[0] = column1[i]
			current[1] = int(column2[i])
			result.append(current)
		current = ['','']


			#result.append(str(column1[i]) + ' | ' + str(column2[i]))


	return result
