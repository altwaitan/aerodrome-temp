from flask import Flask, request, redirect, session, render_template, url_for, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.oauth2.credentials
from googleapiclient.errors import HttpError
from datetime import datetime
import os
import calendar
import pytz


app = Flask(__name__)
app.secret_key = 'Aerodrome'
ourCalendarID = 'c_445aaa2587b481d14101c32aef221cd16f8a071b4bfdddbb76580d66d7953073@group.calendar.google.com'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
CLIENT_SECRETS_FILE = "misc/client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/userinfo.email', 'openid']
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri='http://localhost:5000/authorize')


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
    last_day_of_month = datetime(
        now.year, now.month, calendar.monthrange(now.year, now.month)[1])

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
def home_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('index.html', auth_url=authorization_url, current_page='home')


@app.route('/people')
def people_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('people.html', auth_url=authorization_url, current_page='people')


@app.route('/register')
def register_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('register.html', auth_url=authorization_url)

@app.route('/conduct')
def conduct_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('conduct.html', auth_url=authorization_url, current_page='conduct')

@app.route('/instructions')
def instructions_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('conduct.html', auth_url=authorization_url)

@app.route('/contact')
def contact_page():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return render_template('contact.html', auth_url=authorization_url, current_page='contact')

@app.route('/authorize')
def authorize():
    try:
        flow.fetch_token(authorization_response=request.url)

        if not session['state'] == request.args['state']:
            return 'State does not match!', 400

        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)

        # Get user info and store email in session
        userinfo_service = build('oauth2', 'v2', credentials=credentials)
        try:
            user_info = userinfo_service.userinfo().get().execute()
            session['email'] = user_info.get('email')
        except HttpError as e:
            # Handle error
            print(f"Error fetching user info: {e}")
            return jsonify({'error': 'Failed to fetch user information.'}), 500

        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error during authorization: {e}")
        return "An error occurred during authorization.", 500


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/create-event', methods=['POST'])
def create_event():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    if request.method == 'POST':
        credentials = google.oauth2.credentials.Credentials(
            **session['credentials'])
        service = build('calendar', 'v3', credentials=credentials)

        user_email = session.get('email')
        if not user_email:
            return jsonify({'error': 'User email not found in session.'}), 401

        name = request.form['name']
        email = request.form['email']
        title = request.form['title']
        date = request.form['date']
        start_time = request.form['start-time']
        end_time = request.form['end-time']

        # Create a timezone
        la_timezone = pytz.timezone('America/Los_Angeles')

        start_datetime = la_timezone.localize(
            datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M"))
        end_datetime = la_timezone.localize(
            datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M"))

        # Format the start and end datetimes
        start_datetime_str = start_datetime.isoformat()
        end_datetime_str = end_datetime.isoformat()

        try:
            acl = service.acl().list(calendarId=ourCalendarID).execute()
        except HttpError as e:
            if e.resp.status == 403:
                return jsonify({'error': 'no_permission', 'message': 'You do not have permission to access the calendar.'}), 403
            else:
                return jsonify({'error': 'unknown_error', 'message': 'An unknown error occurred.'}), 500

        # Check if the user has the necessary permissions
        has_permission = False
        for entry in acl['items']:
            if entry['scope']['type'] == 'user' and entry['scope']['value'] == user_email:
                if entry['role'] in ['owner', 'writer']:
                    has_permission = True
                    break

        if not has_permission:
            return jsonify({'error': 'You do not have permission to create events on this calendar.'}), 403

        data = request.json
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

        event = service.events().insert(calendarId=ourCalendarID, body=event).execute()
        return jsonify(event)

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
