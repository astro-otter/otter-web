'''
Some constant configurations for the website frontend
'''
import os

# THIS HAS TO BE THIS TO WORK WITH THE DOCKER NETWORK
# THAT IS WHY THIS BRANCH IS DIFFERENT AND SHOULD
# REMAIN DIFFERENT (BUT CAUGHT UP WITH) MAIN
API_URL = os.environ.get("ARANGO_URL", "http://localhost:8529")
print(f"Connecting to {API_URL}")
WEB_BASE_URL = "/"
print(f"The WEB_BASE_URL for the app is set to {WEB_BASE_URL}")

# a hashmap of page routes that are unrestricted. The only one that shouldn't
# be in here for now is the vetting page
unrestricted_page_routes = {
    os.path.join(WEB_BASE_URL, '/login'),
    os.path.join(WEB_BASE_URL, '/'),
    os.path.join(WEB_BASE_URL, '/search'),
    os.path.join(WEB_BASE_URL, '/upload'),
    os.path.join(WEB_BASE_URL, '/upload/*/success'),
    os.path.join(WEB_BASE_URL, '/api')
}
otterpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "otterdb")

# Vetter Emails to send messages to when there is a new otter upload
vetting_password = os.environ.get("VETTING_PASSWORD", "")
storage_secret = os.environ.get("STORAGE_SECRET", "")
