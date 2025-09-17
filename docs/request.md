can we create oauth tester that setup simple frontend page and all the api that we can use while we develop oauth
we go throuh oauth, and end result, I want to get jwt token on the page
use fast api as backend and whatever frontend simple as possible that work with fastapi
give me plans what you will do

provider will be Thread and we need locally https as Thread doesn't allow us to just use http even if it's local

hey, why didn't you use src folder, rename src/photos-api to match our service, this is scaffold project, so use the existing project and use it by renaming them

Note: should have said that study README.md and existing project structure before you start and then rename it and use it

## Get long lived token

refer to `/Users/universe/project/thrubble-web/docs/reference/threads`
- Now on top of current implementation of getting short lived token, we need to get long lived token
- Show me plan how you will do it


## Diagram

Draw sequence diagram for oauth flow we've implemented in this project, write that in docs/oauth-flow.md

Seems we are using starlette_client for oauth client, however, I prefer to use standard library. Can we make change so that we just use httpx and do oauth flow manually without using starlette_client?
If so, update code and docs/oauth-flow.md