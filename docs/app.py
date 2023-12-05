from flask import Flask, request, redirect, session, render_template_string, render_template
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.oauth2.credentials
from datetime import datetime, timezone
import calendar
import pytz


app = Flask(__name__, static_folder='static')

app.secret_key = 'Quadrotor2017'

# Set up the OAuth 2.0 flow
flow = Flow.from_client_secrets_file(
    'misc/client_secret.json',  
    scopes=['https://www.googleapis.com/auth/calendar'],
    redirect_uri='http://localhost:5000/authorize')

@app.route('/')
def index():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('index.html', auth_url=authorization_url)

@app.route('/authorize')
def authorize():
    flow.fetch_token(authorization_response=request.url)
    
    if not session['state'] == request.args['state']:
        return 'State does not match!', 500

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect('/submit-booking')

def is_overlapping(start_time, end_time, service):
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])

    return len(events) > 0

def count_monthly_events(email, service):
    # Get the first and last day of the current month
    now = datetime.now()
    first_day_of_month = datetime(now.year, now.month, 1)
    last_day_of_month = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

    # Convert to timezone-aware datetime
    la_timezone = pytz.timezone('America/Los_Angeles')
    start_of_month = la_timezone.localize(first_day_of_month)
    end_of_month = la_timezone.localize(last_day_of_month)

    # Get events from Google Calendar
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_of_month.isoformat(),
        timeMax=end_of_month.isoformat(),
        singleEvents=True,
        orderBy='startTime').execute()

    # Count events created by the given email
    events = events_result.get('items', [])
    return sum(1 for event in events if any(attendee.get('email') == email for attendee in event.get('attendees', [])))
    

@app.route('/submit-booking', methods=['GET', 'POST'])
def submit_booking():
    if 'credentials' not in session:
        return redirect('/')

    if request.method == 'POST':
        credentials = google.oauth2.credentials.Credentials(**session['credentials'])
        service = build('calendar', 'v3', credentials=credentials)

        name = request.form['name']
        email = request.form['email']
        title = request.form['title']
        date = request.form['date']
        start_time = request.form['start-time']
        end_time = request.form['end-time']

        # Create a timezone object for Los Angeles
        la_timezone = pytz.timezone('America/Los_Angeles')

        # Parse the date and time from the form
        start_datetime = la_timezone.localize(datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M"))
        end_datetime = la_timezone.localize(datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M"))

        # Format the start and end datetimes in the required format
        start_datetime_str = start_datetime.isoformat()
        end_datetime_str = end_datetime.isoformat()

        # Check for overlapping events
        if is_overlapping(start_datetime, end_datetime, service):
            return "There is already an event scheduled for this time. Please choose another time."
        
        if count_monthly_events(email, service) >= 10:
            return "You have exceeded your monthly limit of event creation."

        # Define the event with formatted start and end times
        event = {
            'summary': title,
            'description': f"Name: {name}, Email: {email}",
            'start': {
                'dateTime': start_datetime_str,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_datetime_str,
                'timeZone': 'America/Los_Angeles',
            },
            'attendees': [{'email': email}],
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {created_event.get('htmlLink')}"

    # HTML form for booking
    return render_template_string('''
        <form method="post">
            Name: <input type="text" name="name"><br>
            Email: <input type="email" name="email"><br>
            Event Title: <input type="text" name="title"><br>
            Date: <input type="date" name="date"><br>
            Start Time: <input type="time" name="start-time"><br>
            End Time: <input type="time" name="end-time"><br>
            <input type="submit" value="Book">
        </form>
    ''')

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    app.run('localhost', 5000, debug=True)
