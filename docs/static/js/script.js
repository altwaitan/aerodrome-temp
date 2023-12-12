document.getElementById('authButton').addEventListener('click', toggleAuth);
document.getElementById('eventForm').addEventListener('submit', createEvent);

function toggleAuth() {
    if (document.getElementById('authButton').innerText === 'Login') {
        window.location.href = '/login';
    } else {
        window.location.href = '/logout';
    }
}

function createEvent(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const eventData = Object.fromEntries(formData.entries());

    fetch('/create-event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(eventData),
    })
    .then(response => {
        if (!response.ok) {
            // If response is not OK, throw an error to be caught in the catch block
            throw response;
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            // Handle specific error message from the server
            document.getElementById('eventCreationMessage').innerText = data.message;
        } else {
            console.log('Success:', data);
            document.getElementById('eventCreationMessage').innerText = 'Event created successfully!';
        }
    })
    .catch((error) => {
        if (error.json) {
            // If the error has a json method, it's a response object
            error.json().then(body => {
                document.getElementById('eventCreationMessage').innerText = body.message || 'An error occurred while creating the event.';
            });
        } else {
            // Handle other types of errors (e.g., network error)
            console.error('Error:', error);
            document.getElementById('eventCreationMessage').innerText = 'An error occurred while creating the event.';
        }
    });
}
