'''
Some constant configurations for the website frontend
'''
import os

# THIS HAS TO BE THIS TO WORK WITH THE DOCKER NETWORK
# THAT IS WHY THIS BRANCH IS DIFFERENT AND SHOULD
# REMAIN DIFFERENT (BUT CAUGHT UP WITH) MAIN
API_URL = "http://localhost:8529"
UI_URL = ""

# a hashmap of page routes that are unrestricted. The only one that shouldn't
# be in here for now is the vetting page
unrestricted_page_routes = {'/login', '/', '/search', '/upload', '/upload/*/success'}
otterpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "otterdb")

# Vetter Emails to send messages to when there is a new otter upload
vetting_password = os.environ.get("VETTING_PASSWORD", "")
storage_secret = os.environ.get("STORAGE_SECRET", "")
