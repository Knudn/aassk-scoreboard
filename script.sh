#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Node.js and npm are required but not installed. Please install them and try again."
    exit 1
fi

# Create the main project directory
PROJECT_NAME="flask_tailwind_project"
mkdir $PROJECT_NAME
cd $PROJECT_NAME

# Create the main application file
cat << EOF > app.py
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
EOF

# Create directories
mkdir -p templates static/{css,js,images} utils tests

# Create static files
touch static/css/style.css
touch static/js/script.js

# Create template files
cat << EOF > templates/base.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Flask Tailwind App{% endblock %}</title>
    <link href="{{ url_for('static', filename='css/output.css') }}" rel="stylesheet">
</head>
<body>
    {% block content %}
    {% endblock %}
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
EOF

cat << EOF > templates/index.html
{% extends "base.html" %}
{% block content %}
<div class="container mx-auto mt-8">
    <h1 class="text-4xl font-bold text-center">Welcome to Flask with Tailwind CSS</h1>
    <p class="text-center mt-4">This is a sample page using Tailwind CSS.</p>
</div>
{% endblock %}
EOF

# Create utility files
touch utils/__init__.py
touch utils/helpers.py

# Create test file
touch tests/test_app.py

# Create requirements file
cat << EOF > requirements.txt
Flask==2.0.1
EOF

# Create README
cat << EOF > README.md
# Flask Tailwind Project

This is a Flask project using Tailwind CSS for styling.

## Setup

1. Activate your virtual environment (if you're using one)
2. Run the Flask app: \`python app.py\`
3. In a separate terminal, run the Tailwind CLI build process: \`npm run build-css\`

EOF

# Create a .gitignore file
cat << EOF > .gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
env/
venv/
pip-log.txt
pip-delete-this-directory.txt

# Flask
instance/
.webassets-cache

# Logs
*.log

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDEs and editors
.idea/
.vscode/
*.swp
*.swo

# Node.js
node_modules/

# Tailwind CSS
static/css/output.css
EOF

# Create package.json
cat << EOF > package.json
{
  "name": "flask-tailwind-project",
  "version": "1.0.0",
  "description": "Flask project with Tailwind CSS",
  "scripts": {
    "build-css": "tailwindcss -i ./static/css/style.css -o ./static/css/output.css --watch"
  },
  "devDependencies": {
    "tailwindcss": "^3.3.0"
  }
}
EOF

# Create tailwind.config.js
cat << EOF > tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

# Update static/css/style.css with Tailwind directives
cat << EOF > static/css/style.css
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Build Tailwind CSS
npm run build-css &

echo "Flask project with Tailwind CSS setup completed!"
echo "Project structure:"
tree -L 2

echo "
To run your Flask app:
1. Ensure you're in the project directory: $PROJECT_NAME
2. Activate the virtual environment: source venv/bin/activate
3. Start the Flask development server: python app.py
4. In a separate terminal, run: npm run build-css (if not already running)
5. Open your browser and navigate to http://127.0.0.1:5000
"

# Deactivate virtual environment
deactivate
