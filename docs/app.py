from flask import Flask, request, redirect, session, render_template, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.oauth2.credentials
from datetime import datetime, timezone
import calendar
import pytz


app = Flask(__name__, static_folder='static')

app.secret_key = 'Quadrotor2017'

flow = Flow.from_client_secrets_file(
    'misc/client_secret.json',  
    scopes=[
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.settings.readonly'
    ],
    redirect_uri='http://localhost:5000/authorize')

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
    now = datetime.now()
    first_day_of_month = datetime(now.year, now.month, 1)
    last_day_of_month = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

    # Convert timezone 
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

def has_edit_permissions(email, service, calendar_id='primary'):
    try:
        acl = service.acl().list(calendarId=calendar_id).execute()
        for entry in acl['items']:
            if entry.get('scope', {}).get('type') == 'user' and entry['scope']['value'] == email:
                role = entry.get('role')
                return role in ['owner', 'writer']  
        return False
    except Exception as e:
        print(f"Error checking permissions: {e}")
        return False

@app.route('/')
def index():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('index.html', auth_url=authorization_url)

@app.route('/authorize')
def google_authorize():
    state = session['state']
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('submit_booking'))  

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/submit-booking', methods=['GET', 'POST'])
def submit_booking():
    if 'credentials' not in session:
        if 'X-Requested-With' in request.headers and request.headers['X-Requested-With'] == 'XMLHttpRequest':
            return "Please login to submit a booking."
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

        # Create a timezone
        la_timezone = pytz.timezone('America/Los_Angeles')

        start_datetime = la_timezone.localize(datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M"))
        end_datetime = la_timezone.localize(datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M"))

        # Format the start and end datetimes
        start_datetime_str = start_datetime.isoformat()
        end_datetime_str = end_datetime.isoformat()

        if is_overlapping(start_datetime, end_datetime, service):
            return "There is already an event scheduled for this time. Please choose another time."
        
        if count_monthly_events(email, service) >= 10:
            return "You have exceeded your monthly limit of event creation."
        
        if not has_edit_permissions(email, service):
            return "You do not have permission to create events in this calendar."

        event = {
            'summary': title,
            'description': f"Title: {title}\nName: {name}\nEmail: {email}",
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
        return "Thank you! Your event has been created successfully."

    # HTML form for booking
    return render_template('index.html')

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
