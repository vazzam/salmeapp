from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import json

# Create a GoogleAuth instance and authenticate with a service account
gauth = GoogleAuth()
scope = ['https://www.googleapis.com/auth/drive']
# print(json.loads('service_account2.json'))
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('./service_account.json')
# credentials = ServiceAccountCredentials.from_json_keyfile_name('service_account2.json', scope)

# Create a GoogleDrive instance and connect to your Google Drive
drive = GoogleDrive(gauth)
final_name = 'prueba'
gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})