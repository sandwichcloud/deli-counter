import cherrypy
import github
import github.AuthenticatedUser
import requests
import requests.exceptions
from github.GithubException import TwoFactorException, GithubException, BadCredentialsException
from simple_settings import settings
from sqlalchemy_utils.types.json import json

from deli_counter.auth.validation_models.github import RequestGithubAuthorization, RequestGithubToken
from deli_counter.http.mounts.root.routes.v1.validation_models.auth import ResponseOAuthToken
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class GithubAuthRouter(Router):
    def __init__(self, driver):
        super().__init__(uri_base='github')
        self.driver = driver

    @Route(route='authorization', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestGithubAuthorization)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def authorization(self):  # Used to get token via API (username and password Auth Flow)
        request: RequestGithubAuthorization = cherrypy.request.model

        user_github_client = github.Github(request.username, request.password)
        github_user: github.AuthenticatedUser.AuthenticatedUser = user_github_client.get_user()

        try:
            authorization = github_user.create_authorization(
                scopes=['user:email', 'read:org'],
                note='Sandwich Cloud Authorization',
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                onetime_password=request.otp_code
            )
        except TwoFactorException:
            cherrypy.response.headers['X-GitHub-OTP'] = '2fa'
            raise cherrypy.HTTPError(401, "OTP Code Required")
        except BadCredentialsException:
            raise cherrypy.HTTPError(404, "Invalid credentials")
        except GithubException as e:
            self.logger.exception("Error while validating GitHub authorization")
            raise cherrypy.HTTPError(424, "Backend error while talking with GitHub: " + json.dumps(e.data))

        # Call api with the user's token
        token_github_client = github.Github(authorization.token)
        github_user = token_github_client.get_user()
        if self.driver.check_in_org(github_user) is False:
            raise cherrypy.HTTPError(403, "User not a member of GitHub organization: '" + settings.GITHUB_ORG + "'")

        with cherrypy.request.db_session() as session:
            token = self.driver.generate_user_token(session, github_user.login)
            session.commit()
            session.refresh(token)

        return ResponseOAuthToken.from_database(token)

    @Route(route='token', methods=[RequestMethods.OPTIONS])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def token_options(self):
        # This is required for EmberJS for some reason?
        return {}

    @Route(route='token', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestGithubToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def token(self):  # Used to get token via Web UI (Authorization Code Auth Flow)
        request: RequestGithubToken = cherrypy.request.model

        r = requests.post('https://github.com/login/oauth/access_token', json={
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': request.authorizationCode
        }, headers={'Accept': 'application/json'})

        if r.status_code == 404:
            raise cherrypy.HTTPError(404, "Unknown Authorization Code")
        elif r.status_code != 200:
            try:
                r.raise_for_status()
            except request.exceptions.RequestException as e:
                self.logger.exception("Error while validating GitHub access token")
                raise cherrypy.HTTPError(424, "Backend error while talking with GitHub: " + e.response.text)

        access_token_data = r.json()
        token_github_client = github.Github(access_token_data['access_token'])
        github_user = token_github_client.get_user()
        if self.driver.check_in_org(github_user) is False:
            raise cherrypy.HTTPError(403, "User not a member of GitHub organization: '" + settings.GITHUB_ORG + "'")

        with cherrypy.request.db_session() as session:
            token = self.driver.generate_user_token(session, github_user.login)
            session.commit()
            session.refresh(token)

        return ResponseOAuthToken.from_database(token)
