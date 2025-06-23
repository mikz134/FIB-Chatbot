# Set this to False if going to production
DEBUG = True

# Set this to random value when going to production
SECRET_KEY = 'development'

# App credentials lazy load configuration
# Read: https://flask-oauthlib.readthedocs.io/en/latest/client.html#lazy-configuration
# Get them: https://raco.fib.upc.edu/api/v2/o/
RACO = {
    'consumer_key': 'btYurHdRXEoR5dcGc3W9v36fhEfk7jvrJWUIcO7K',
    'consumer_secret': 'f6XtVQJ0SwwXU6qxOMNgEXy61xydxQWPh3neiiU6PCobl7poabZefBuWuUzTkLkLZiNrhP5d87tpABi9ULbltbTgzW2DYQhgn2zZCvdcKFVimemyln5msXrikGeEHbj3'
}