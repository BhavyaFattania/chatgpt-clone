from flask import Flask
from server.backend import Backend_Api
from server.website import Website
import os

app = Flask(__name__, template_folder='./../client/html')

# Configuration for the application
config = {
    'groq_api_key': "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",  # Get from environment variable
    'proxy': {
        'enable': False,
        'http': '',
        'https': ''
    }
}

# Initialize the backend API
backend_api = Backend_Api(app, config)

# Initialize the website
website = Website(app)

# Register routes for backend API
for route, data in backend_api.routes.items():
    app.add_url_rule(
        route,
        view_func=data['function'],
        methods=data['methods']
    )

# Register routes for website
for route, data in website.routes.items():
    app.add_url_rule(
        route,
        view_func=data['function'],
        methods=data['methods']
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1337, debug=True)