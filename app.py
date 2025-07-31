#Importing Packages
from flask import Flask
from controller_files import *
from controller_files.bot_controller import Ai_bot

# Initializing the Flask web app object  (Name is nothing but my location where actually something is residing)
# app is the name of my restaurant Flask is the tool kit required for my kitchen and __name__ is my location
app = Flask(__name__)

# My initial entry point 
@app.route("/")
def Home():
    return "This is my home Page"

if __name__ == "__main__":
    app.run(debug=True)


