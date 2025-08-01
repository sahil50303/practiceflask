from app import app

@app.route("/donations")
def donations():
    return "this is my Donations page"

