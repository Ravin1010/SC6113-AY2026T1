# 6113 dapp

from flask import Flask, render_template, request
import sqlite3
import datetime

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index(): 
    return(render_template("index.html"))

@app.route("/main", methods=["GET", "POST"])
def main(): 
    q = request.form.get("q")
    time = datetime.datetime.now()
    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('INSERT INTO user (name,timestamp) VALUES(?,?)',(q,time))
    conn.commit()
    c.close()
    conn.close()
    return(render_template("main.html"))

@app.route("/transferMoney", methods=["GET", "POST"])
def transferMoney(): 
    return(render_template("transferMoney.html"))

@app.route("/depositMoney", methods=["GET", "POST"])
def depositMoney():
    return render_template("depositMoney.html")

@app.route("/viewUser", methods=["GET", "POST"])
def viewUser(): 
    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('select * from user')
    r = ""
    for i in c:
        print(i)
        r = r + str(i)
    print(r)
    c.close()
    conn.close()
    return(render_template("viewUser.html",r=r))

@app.route("/deleteUser", methods=["POST"])
def deleteUser():
    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('DELETE FROM user')
    conn.commit()
    c.close()
    conn.close()

    return render_template("main.html")

if __name__ == "__main__": 
    app.run()

