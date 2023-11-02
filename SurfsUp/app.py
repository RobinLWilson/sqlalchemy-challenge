# Import the dependencies.
import numpy as np
import pandas as pd
import datetime as dt

from flask import Flask, jsonify

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import and_, create_engine, text, inspect, func
#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(autoload_with=engine)

# Save references to each table
measurement = Base.classes.measurement
station = Base.classes.station

# Create our session (link) from Python to the DB
session = Session(engine)

#################################################
# Flask Setup
#################################################
app = Flask(__name__)



#################################################
# Flask Routes
#################################################
@app.route("/")
def home():
    """List all available api routes."""
    return (
        f"Available Routes:<br/>"
        f"/api/v1.0/precipitation<br/>"
        f"/api/v1.0/stations<br/>"
        f"/api/v1.0/tobs<br/>"
        f"/api/v1.0/start_date/ <br/>"
        f"Replace 'start_date' with date of your choice to the end of the URL in this format: YEAR-MO-DA<br/>"
        f"<br/>"
        f"/api/v1.0/start_date/end_date/ <br/>"
        f"Replace 'start_date' with date of your choice to the end of the URL in this format: YEAR-MO-DA<br/>"
        f"Replace 'end_date' with date of your choice to the end of the URL in this format: YEAR-MO-DA<br/>"
    )

@app.route('/api/v1.0/precipitation')
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Calculate the date one year ago from the last date in the database
    latest_date = session.query(func.max(measurement.date)).scalar()
    one_year_ago = (dt.datetime.strptime(latest_date, '%Y-%m-%d') - dt.timedelta(days=365)).strftime('%Y-%m-%d')

    # Query the precipitation data for the last 12 months
    results = session.query(measurement.date, measurement.prcp).filter(measurement.date >= one_year_ago).all()

    session.close()

    # Convert the results into a dictionary with date as the key and prcp as the value
    precipitation_data = {date: prcp for date, prcp in results}

    return jsonify(precipitation_data)

@app.route('/api/v1.0/stations')
def stations():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query the list of stations
    station_data = session.query(station.station, station.name).all()

    session.close()

    # Convert the list of stations into a JSON list
    station_list = [{"station_id": station[0], "name": station[1]} for station in station_data]

    return jsonify(station_list)

@app.route('/api/v1.0/tobs')
def tobs():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Calculate the date one year ago from the last date in the database
    last_date = session.query(func.max(measurement.date)).scalar()
    one_year_ago = (dt.datetime.strptime(last_date, '%Y-%m-%d') - dt.timedelta(days=365)).strftime('%Y-%m-%d')

    # Query temperature observations for the most active station for the last year
    most_active_station = session.query(measurement.station).group_by(measurement.station).order_by(func.count(measurement.id).desc()).first()[0]
    tobs_data = session.query(measurement.date, measurement.tobs).filter(measurement.station == most_active_station, measurement.date >= one_year_ago).all()

    # Convert the results into a JSON list of temperature observations
    tobs_list = [{'station': most_active_station, 'date': date, 'tobs': tobs} for date, tobs in tobs_data]

    return jsonify(tobs_list)

@app.route('/api/v1.0/<start_date>/')
@app.route('/api/v1.0/<start_date>/<end_date>')
def temperature_stats_range(start_date, end_date=None):
    session = Session(engine)
    sel = [func.min(measurement.tobs), func.avg(measurement.tobs), func.max(measurement.tobs)]
    #start date set by user:
    start_date = dt.datetime.strptime(start_date, '%Y-%m-%d').date()
    #most recent date in dataset:
    latest_date = session.query(func.max(measurement.date)).scalar()
    #first date in the dataset:
    earliest_date = session.query(func.min(measurement.date)).scalar()
    earliest_date = dt.datetime.strptime(earliest_date, '%Y-%m-%d').date()

    #check to see if start date is before the earliest date in the dataset
    if start_date < earliest_date:
        return jsonify({'404 error': 'Start date is before the start of the data.'}), 400
    
    # Check if end_date is provided
    if end_date:
        end_date = dt.datetime.strptime(str(end_date), '%Y-%m-%d').date()
        # Define the query to calculate temperature statistics for the specified date range
        temperature_stats = session.query(*sel).filter(measurement.date >= start_date).filter(measurement.date <= end_date).all()
    else:
        # If no end_date is provided, query only based on start_date
        temperature_stats = session.query(*sel).filter(measurement.date >= start_date).all()

    session.close()

    if temperature_stats:
        temp_stats_dict = {
            'start_date': start_date,
            'end_date': end_date if end_date else latest_date,
            'temperature_statistics': {
                'min_temperature': temperature_stats[0][0],
                'average_temperature': temperature_stats[0][1],
                'max_temperature': temperature_stats[0][2]
            }
        }
        return jsonify(temp_stats_dict)
    else:
        return jsonify({'error': 'No temperature data available for the specified date range.'}), 404
    
if __name__ == "__main__":
    app.run(debug=True)
