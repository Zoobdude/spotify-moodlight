from spotipy.oauth2 import SpotifyOAuth

scope = "user-read-currently-playing"

print("GET REFRESH TOKEN")
print("---------------")
print("Go to https://developer.spotify.com/dashboard and create an app.")
print("The name and description can be anything.")
print("The redirect URI must be http://127.0.0.1")
print("After creating the app, go to the app's page and click edit settings.")

client_id = input("Enter your client id: ")

print("Click the small hyperlink that says 'Show Client Secret'")
client_secret = input("Enter your client secret: ")

print("----------------")

sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri='http://127.0.0.1', scope=scope)
auth_url = sp_oauth.get_authorize_url()

print("Please copy and paste the following URL into your browser.")
print(auth_url})
print("After logging in and accepting permissions, you will be sent to an error page, this is expected.")

response = input("Enter the URL you were redirected to: ")
print("----------------\n")

code = sp_oauth.parse_response_code(response)
token_info = sp_oauth.get_cached_token()

# Get the refresh token
refresh_token = token_info['refresh_token']

print("Your refresh token is:")
print(refresh_token)
print()
print("Please copy and paste this into the refresh_token.txt file in the pico directory.")