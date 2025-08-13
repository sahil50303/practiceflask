#Importing Packages
from flask import Flask


# Initializing the Flask web app object  (Name is nothing but my location where actually something is residing)
# app is the name of my restaurant Flask is the tool kit required for my kitchen and __name__ is my location

app = Flask(__name__)

# My initial entry point 
@app.route("/")
def Home():
    return "This is my home Page"

import controller_files.bot_controller as bot
import controller_files.receipt_API as donations
# To run in debug mode:
#we run $env:FLASK_ENV = "development"  this is not working for now work as it is




