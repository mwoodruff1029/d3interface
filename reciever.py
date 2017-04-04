#!/usr/bin/env python

import socket
import json
import csv
import time
import datetime
import threading
import psycopg2

#from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, cast

TCP_IP = '127.0.0.1'
TCP_PORT = 11111
BUFFER_SIZE = 1024

def launchServer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', TCP_PORT))
    s.listen(1)

    conn, addr = s.accept()

    while True:
        data = conn.recv(BUFFER_SIZE)
        if not data: break
        #print data
        # add data to our database
        data = json.loads(data)
        entry = Water_usage(data['readingOut'], data['readingIn'], data['timestamp'])
        db.session.add(entry)
        db.session.commit()

# Flask app for responding to http requests
# and connecting to database
db_conn = 'postgresql+psycopg2://sendes:pass@localhost/sr'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_conn
db = SQLAlchemy(app)

# class for database manipulation
class Water_usage(db.Model):
        outdoor = db.Column(db.Numeric)
        indoor = db.Column(db.Numeric)
        id = db.Column(db.BigInteger, primary_key=True)
        ts = db.Column(db.DateTime)

        def __init__(self, outdoor, indoor, ts):
            self.outdoor = outdoor
            self.indoor = indoor
            # we won't require an id value until we figure out what we want this value
            # to actually represent 
            #self.id = id
            self.ts = datetime.datetime.strptime(ts, '%m/%d/%y %H:%M')

        @property
        def serialize(self):
            """Return object data in easily serializeable format"""
            return {
                'id' : self.id,
                'outdoor': float(self.outdoor),
                'indoor' : float(self.indoor),
                'timestamp' : str(self.ts)
            }

@app.route("/")
def hello():
    return render_template('index2.html')

# this returns all readings available
@app.route("/sha/v1.0/readings/", methods=['GET'])
def get_all_meter_readings():
    return jsonify(meters=[i.serialize for i in Water_usage.query.all()])

@app.route("/sha/v1.0/readings/daily", methods=['GET'])
def get_daily_readings():

    # check to see if the user submitted a max number of requests
    data = request.args
    max = 10
    if ('max' in data.keys()):
        max = int(data['max'])

    # get the sum of indoor and outdoor readings by date, limiting by the max number of values the client wants
    agg = db.session.query(
        db.func.sum(Water_usage.outdoor),
        db.func.sum(Water_usage.indoor),
        cast(Water_usage.ts,Date)).group_by(cast(Water_usage.ts, Date)).order_by(cast(Water_usage.ts,Date).desc()).limit(max)
    return jsonify(meters=[{'outdoor': float(str(i[1])), 'indoor': float(str(i[0])), 'timestamp': str(i[2])} for i in agg])

# this returns the most current readings, up to a max submitted by the requester
# the default max is 10
@app.route("/sha/v1.0/readings/current/", methods=['GET'])
def get_current_meter_readings():
    data = request.args
    max = 10
    if ('max' in data.keys()):
        max = int(data['max'])
    result = db.session.query(Water_usage).order_by(Water_usage.ts.desc()).limit(max)
    #print result
    return jsonify(meters=[i.serialize for i in result])

# this returns the readings that have occurred since the timestamp that is passed
@app.route("/sha/v1.0/readings/<string:timestamp>", methods=['GET'])
def get_meter_readings(timestamp):
    last_reading = datetime.datetime.strptime(timestamp, '%Y-%m-%d').date()
    result = db.session.query(Water_usage).filter(Water_usage.ts > last_reading).all()
    return jsonify(readings=[i.serialize for i in result])
    
if __name__ == "__main__":
    t = threading.Thread(target=launchServer)
    t.daemon = True
    t.start()
    # run flask server on local ip address so it can be accessed
    # by other devices on the network that know its IP address
    app.run(host='0.0.0.0')





