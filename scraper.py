#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import re
import time
import gspread
import pdb
import json
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup

guild_file = "bsh.txt"
guild_url = "https://swgoh.gg/g/944/black-sun-heroes/"
unit_url = "https://swgoh.gg/"

def RetrievePage(url):
  return requests.get(url).text 

def SoupParse(page):
  return BeautifulSoup(page,'html.parser')

def GetUsers(soup,id_regex,name_regex):
  for link in soup.find_all('a'):
    if '/u/' in str(link): 
      user_id = re.search(id_regex,str(link)).group(0)
      user_name = re.search(name_regex,str(link)).group(0)
      users[user_id] = {'name':user_name}
  return users

def GetUnits(soup,id_regex,name_regex,alignment_regex):
  for character in soup.find_all('a', class_=re.compile('character')):
    if "/characters/" in str(character):
      unit_id = re.search(id_regex,str(character)).group(0)
      unit_name = re.search(name_regex,str(character)).group(0).replace('&quot;','')
      unit_alignment = re.search(alignment_regex,str(character)).group(0)
      units[unit_id] = {'name':unit_name,'alignment':unit_alignment}
      print 'Parsed unit',units[unit_id]['name']
  return units


guild_soup = SoupParse(RetrievePage(guild_url))
unit_soup = SoupParse(RetrievePage(unit_url))

users = {}
# Grab word characters that follow a /u/
user_id_regex = re.compile('(?<=/u/)[\w-]+')
user_name_regex = re.compile('[\w ]+(?=</a>)')

# Find all the links in the page and filter out the users from those links
users = GetUsers(guild_soup,user_id_regex,user_name_regex)

units = {}
unit_id_regex = re.compile('(?<=/characters/)[\w-]+')
unit_name_regex = re.compile('(?<=<h5>)[\wÎ\(\)\" -]*')
unit_alignment_regex= re.compile('(?<=media-body character )[\w]+')

# Grab all the potential units by searching for /characters/
units = GetUnits(unit_soup,unit_id_regex,unit_name_regex,unit_alignment_regex)

user_base_url = 'https://swgoh.gg/u/'
user_base_dir = 'users'
for user in users:
  print "Getting data for",user_base_url + user
  url = requests.get(user_base_url + user + '/collection')
  file = open(user_base_dir + '/' + user,'w')
  file.write(url.content)
  file.close()
  time.sleep(5)

# Compile all of our regular expressions we're going to parse for
user_units = {}
user_unit_id_regex = re.compile('(?<=collection\/|characters\/)[\w-]+')
user_unit_gear_regex = re.compile('(?<=gear-t)[\d]+')
user_unit_level_regex = re.compile('(?<=full-level\">)[\d]+')
user_unit_star_regex = re.compile('(?<=star star)[\d](?! star)')
user_unit_power_regex = re.compile('(?<=Power )[\d,]+')
output_path = 'bsh-toons/'

for user in users:
  user_units[user] = {}
  user_soup = BeautifulSoup(open('users/'+user),'html.parser')
  user_units_soup = user_soup.find_all("div",class_="collection-char")
  print 'Getting collection for',user
  file = open(output_path+user,'w')
  file.write('unit,stars,level,gear,power\n')
  for item in user_units_soup:
    try:
      user_unit_id = re.search(user_unit_id_regex,str(item)).group(0)
    except:
      user_unit_id = '-'
    try:
      user_unit_gear = re.search(user_unit_gear_regex,str(item)).group(0)
    except:
      user_unit_gear = '0'
    try:
      user_unit_level = re.search(user_unit_level_regex,str(item)).group(0)
    except:
      user_unit_level = '0'
    try:
      user_unit_star = re.findall(user_unit_star_regex,str(item))[-1]
    except:
      user_unit_star = '0'
    try:
      user_unit_power = re.findall(user_unit_power_regex,str(item))[-1].replace(',','')
    except:
      user_unit_power = '0'
    user_units[user][user_unit_id] = {'gear':user_unit_gear,'level':user_unit_level,'star':user_unit_star,'power':user_unit_power}
    file.write(units[user_unit_id]['name']+','+user_unit_star+','+user_unit_level+','+user_unit_gear+','+user_unit_power+'\n')
  file.close()

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('Feritas-e280813e26b6.json',scope)
gc = gspread.authorize(credentials)

guild_sheet = gc.open('Black Sun Heroes')
units_sheet = guild_sheet.worksheet('Units')

# Set up roster sheet
print 'Clearing unit sheet'
for col in range(3,units_sheet.col_count):
  units_sheet.update_cell(1,col,'') 

# Start at the second row since our first is a header
row = 2
# Set up list of toons
print 'Setting up list of units'
for unit in sorted(units):
  print units[unit]['name']
  units_sheet.update_cell(row,1,units[unit]['name'])
  units_sheet.update_cell(row,2,unit)
  row += 1

# Variables we'll need
csv_data_url = 'http://cidrick.org/bsh-toons/'

for user,name in sorted(users.iteritems(), key=lambda (k,v): (v,k)):

  # Create their sheet if they don't have it already
  try:
    user_sheet = guild_sheet.add_worksheet(name['name'],rows=120,cols=4)
    print 'Setting up new sheet for',name['name']
  except:
    user_sheet = guild_sheet.worksheet(name['name'])
    print user,'user sheet already found, continuing'
  
  # Link our importdata
  try:
    user_sheet.update_acell('A1','=ImportData("'+csv_data_url+user+'")')
  except:
    print 'Unable to insert importdata cell for user',name['name'],', continuing'

# Now we'll go back to our unit sheet and add individual roster formulas
col = 3 
for user,name in sorted(users.iteritems(), key=lambda (k,v): (v,k)):
  try:
    units_sheet.update_cell(1,col,name['name'])
  except:
    print 'Unable to update header column with user',name['name'],', continuing'

  col += 1
