from app import app

@app.route("/donations",methods=["GET","POST"])
def donations():
    return "this is my Donations page"

