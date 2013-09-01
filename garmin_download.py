#!/usr/bin/env python

#     ./garmin_download.py -u <username> -p <password> -t <begintime[2013-08-01]>
# This is a command-line utility for the bulk-downloading of run data from
# the connect.garmin.com web application, which has lackluster export
# capabilities.
#
# Using this code is a matter of your own relationship with Garmin Connect
# and their TOS. I can't imagine this being very destructive to their service,
# and it's just filling in a hole in their existing service.
#
# It's built against Garmin Connect as of Step 1, 2013. It's a scraper:
# thus if Garmin changes, this **will break**.
#
# This script requires  utility: mechanize
# intall it with pip
# referece: http://gist.github.com/tmcw/1098861. Thanks.

import mechanize
import json
import os, sys, getopt
from datetime import datetime
from xml.dom import minidom


LOGIN_PAGE = "https://connect.garmin.com/signin"
ACTIVITIES_SEARCH = "http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?_dc=1220170621856&start=%d&limit=30"
GPX_EXPORT = "http://connect.garmin.com/proxy/activity-service-1.1/gpx/activity/%d?full=true"
KML_EXPORT = "http://connect.garmin.com/proxy/activity-service-1.0/kml/activity/%d?full=true"
TCX_EXPORT = "http://connect.garmin.com/proxy/activity-service-1.0/tcx/activity/%d?full=true"

DOWNLOAD_DIR = "GarminDown"
index_file = 0


def parseArgument(argv):
    user = ''
    password = ''
    begintime = ''
    howto = 'garmin_download.py -u <username> -p <password> -t <begintime[2013-08-01]>'
    try:
        opts, args = getopt.getopt(argv,"hu:p:t:",["user=","password=","begintime="])
    except getopt.GetoptError:
        print howto
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print howto
            sys.exit()
        elif opt in ("-u", "--user"):
            user = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-t", "--begintime"):
            begintime = arg
            
    if user == '' or password == '':
        print howto
        sys.exit(2)
    return (user, password, begintime)

def initialBrowser(br):
    br.set_handle_robots(False)
    br.set_handle_refresh(False)
    br.addheaders = [('User-agent', 'Firefox')]

def login(br, user, password):
    response = br.open(LOGIN_PAGE)
    br.select_form("login")         # works when form has a name
    br['login:loginUsernameField'] = user
    br['login:password'] = password
    br.method = "POST"
    response = br.submit()
    if br.title().find('Sign In') != -1:
        print ("Login incorrect!")
        sys.exit(1)
    response
    
def createDirectory():
    if not os.path.exists(DOWNLOAD_DIR):
        os.mkdir(DOWNLOAD_DIR)

def activities(br, beginTime):
    isStop = False
    while True:
        response = br.open(ACTIVITIES_SEARCH % int(index_file))
        jsonRoot= json.loads(response.read())
        if 'activities' in jsonRoot['results']:
            for x in jsonRoot['results']['activities']:
                if isStopDownload(x['activity']['beginTimestamp']['value'], beginTime):
                    isStop = True
                    break
                else:
                    download_file(br, x['activity']['activityId'])
        else:
            break
        if isStop:
            break
    
def download_file(br, id):
    print "."
    global index_file
    br.retrieve(TCX_EXPORT %int(id),"./%s/%d.tmp" %(DOWNLOAD_DIR, index_file))
    index_file = index_file + 1
    
def isStopDownload(actTime, beginTime):
    if beginTime == '':
        if index_file < 30:
            return False
        else:
            return True
    else:
        t1 = datetime.strptime(actTime, "%Y-%m-%d")
        t2 = datetime.strptime(beginTime, "%Y-%m-%d")
        if t2 <= t1:
            return False
        else:
            return True

def mergeActivities():
    #merge 30 activities into one
    NumAct = 30
    NumIter = index_file / NumAct
    for i in range(NumIter):
        mergeAct(i * NumAct, (i + 1) * NumAct)
    if index_file > (NumIter * NumAct):
        mergeAct(NumIter * NumAct, index_file)
    deleteTmpFiles()

def mergeAct(begin, end):
    NewFileName = "./%s/%d-%d.tcx" %((DOWNLOAD_DIR, begin + 1, end))
    xmldoc = minidom.parse("./%s/%d.tmp" %(DOWNLOAD_DIR, begin))
    elemActs = xmldoc.getElementsByTagName('Activities')
    elemAct = xmldoc.getElementsByTagName('Activity')
    for a in elemAct:
        if a.attributes['Sport'].value == 'Other':
            a.attributes['Sport'].value = 'Swimming'
    for i in range(begin + 1, end):
        xmldocMerge = minidom.parse("./%s/%d.tmp" %(DOWNLOAD_DIR, i))
        elemAct = xmldocMerge.getElementsByTagName('Activity')
        for a in elemAct:
            if a.attributes['Sport'].value == 'Other':
                a.attributes['Sport'].value = 'Swimming'
            elemActs[0].appendChild(a)
    xmldoc.writexml(open(NewFileName, 'w+'))

def deleteTmpFiles():
    for i in range(index_file):
        os.remove("./%s/%d.tmp" %(DOWNLOAD_DIR, i))
def main(argv):
    user, password, beginTime = parseArgument(argv)
    br = mechanize.Browser()
    initialBrowser(br)
# One needs to log in to get access to private runs. Mechanize will store
# the session data for the API call that cames next.
    home_page = login(br, user, password)
    createDirectory()
    print "Dowloading runs..."
    activities(br, beginTime)
    mergeActivities()

    
if __name__ == "__main__":
    main(sys.argv[1:])
