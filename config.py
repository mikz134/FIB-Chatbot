# Set this to False if going to production
DEBUG = True

# Set this to random value when going to production
SECRET_KEY = 'development'

# App credentials lazy load configuration
# Read: https://flask-oauthlib.readthedocs.io/en/latest/client.html#lazy-configuration
# Get them: https://raco.fib.upc.edu/api/v2/o/
RACO = {
    'consumer_key': 'KEY_NAME',
    'consumer_secret': 'API_KEY'
}
