This guide explains how to use the Authorization Window to get permissions from Threads users for short-lived Threads user access tokens.

Step 1: Get Authorization
The Authorization Window allows app users to grant your app permissions and short-lived Threads user access tokens. After a user logs in and chooses which data to allow your app to access, we will redirect the user to your app and include an authorization code, which you can then exchange for a short-lived access token.

To begin the process, get the Authorization Window and present it to the user:

https://threads.net/oauth/authorize
  ?client_id=<THREADS_APP_ID>
  &redirect_uri=<REDIRECT_URI>
  &scope=<SCOPE>
  &response_type=code
  &state=<STATE> // Optional
If accessing the Authorization Window from an Android mobile system, make sure to open the URL in the native webview or browser and not the native app.

An example of how you can achieve this with JavaScript:

window.open(url, '_system');`
Parameters
Note: All parameters except state are required.

Name	Description
client_id

numeric string
Required.
Your Threads App ID displayed in App Dashboard > App settings > Basic > Threads App ID.
Example: 990602627938098

redirect_uri

string
Required.
A URI where we will redirect users after they allow or deny permission requests. Make sure this exactly matches one of the base URIs in your list of valid OAuth URIs. Keep in mind that the App Dashboard may have added a trailing slash to your URIs, so we recommend that you verify by checking the list.
Example: https://socialsizzle.herokuapp.com/auth/

response_type

string
Required.
Set this value to code.

scope

comma-separated or space-separated list
Required.
A comma-separated list, or URL-encoded space-separated list, of permissions to request from the app user.
Note: threads_basic is required.
Values: threads_basic, threads_content_publish, threads_read_replies, threads_manage_replies, threads_manage_insights

state

string
An optional value indicating a server-specific state. For example, you can use this to protect against CSRF issues. We will include this parameter and value when redirecting the user back to you.
Example: 1

Sample Authorization Window URL
https://threads.net/oauth/authorize
  ?client_id=990602627938098
  &redirect_uri=https://socialsizzle.herokuapp.com/auth/
  &scope=threads_basic,threads_content_publish
  &response_type=code
Successful Authorization
If authorization is successful, we will redirect the user to your redirect_uri and pass you an authorization code through the code query string parameter. Capture the code so your app can exchange if for a short-lived Threads User Access Token.

Authorization codes are valid for 1 hour and can only be used once.

Sample Successful Authentication Redirect
https://socialsizzle.herokuapp.com/auth/?code=AQBx-hBsH3...#_
Note: #_ will be appended to the end of the redirect URI, but it is not part of the code itself, so strip it out.

Canceled Authorization
If the user cancels the authorization flow, we will redirect the user to your redirect_uri and append the following error parameters.

Note: It is your responsibility to fail gracefully in these situations and display an appropriate message to your users.

Error Parameter	Description
error

acceess_denied

error_reason

user_denied

error_description

The+user+denied+your+request

Sample Canceled Authorization Redirect
https://socialsizzle.herokuapp.com/auth/?error=access_denied
  &error_reason=user_denied
  &error_description=The+user+denied+your+request
Step 2: Exchange the Code For a Token
Once you receive a code, exchange it for a short-lived access token by sending a POST request to the following endpoint:

POST https://graph.threads.net/oauth/access_token
Parameters
Include the following parameters in your POST request body.

Name	Description
client_id

numeric string
Required.
Your Threads App ID displayed in App Dashboard > App settings > Basic > Threads App ID.
Example: 990602627938098

client_secret

string
Required.
Your Threads App Secret displayed in App Dashboard > App settings > Basic > Threads App secret.
Example: a1b2C3D4

code

string
Required.
The authorization code we passed you in the code parameter when redirecting the user to your redirect_uri.
Example: AQBx-hBsH3...

grant_type

string
Required.
Set this value to authorization_code.

redirect_uri

string
Required.
The redirect URI you passed us when you directed the user to our Authorization Window. This must be the same URI or we will reject the request.
Example: https://socialsizzle.heroku.com/auth/

Sample Request
curl -X POST \
  https://graph.threads.net/oauth/access_token \
  -F client_id=990602627938098 \
  -F client_secret=eb8c7... \
  -F grant_type=authorization_code \
  -F redirect_uri=https://socialsizzle.herokuapp.com/auth/ \
  -F code=AQBx-hBsH3...
Sample Success Response
If successful, the API will return a JSON payload containing the app user's short-lived access token and User ID.

{
  "access_token": "THQVJ...",
  "user_id": 17841405793187218
}
Capture the access_token value. This is the user’s short-lived Threads user access token, which your app can use to access Threads API endpoints.

Sample Rejected Response
If the request is malformed in some way, the API will return an error.

{
  "error_type": "OAuthException",
  "code": 400,
  "error_message": "Matching code was not found or was already used"
}
