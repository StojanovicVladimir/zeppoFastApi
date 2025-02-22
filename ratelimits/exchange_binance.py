from binance.client import Client

# Initialize the Binance client for Testnet
API_KEY = 'JaleXRJvHAKlUO5KELCcf87vPLiEcunaEDAEhzF3KOaj7xUX3zPOmhp3h4SvNSbM'  # Replace with your Testnet API key
API_SECRET = 'PDrXkxOv4PKzMQxypiTUFhFQqoTlMtWUSCNbSdxd3Xh35JzHIyctmMdBBRN1L1QD'  # Replace with your Testnet API secret

client = Client(API_KEY, API_SECRET)

# Build the URL for exchange info
url = client.API_URL + "/api/v3/exchangeInfo"

# Make a direct GET request using the client's session
response = client.session.get(url)

# Print the raw response headers
print("Response Headers:")
print(response.headers)