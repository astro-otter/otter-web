'''
Some constant configurations for the website frontend
'''
import os

# THIS HAS TO BE THIS TO WORK WITH THE DOCKER NETWORK
# THAT IS WHY THIS BRANCH IS DIFFERENT AND SHOULD
# REMAIN DIFFERENT (BUT CAUGHT UP WITH) MAIN
API_URL = "http://localhost:8529"
UI_URL = ""

# Vetter Emails to send messages to when there is a new otter upload
vetter_emails = os.environ.get("VETTER_EMAILS", "").split(";")
