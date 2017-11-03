from unittest.mock import patch, MagicMock

from github import BadCredentialsException
from github.Authorization import Authorization
from github.GithubException import TwoFactorException, GithubException
from github.Organization import Organization
from github.Team import Team

from deli_counter.test.base import DeliTestCase, fake


# TODO: assert all responses
# TODO: test model validations

class TestAuthNGithubAuthorization(DeliTestCase):
    def test_invalid_creds(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.side_effect = BadCredentialsException(404, "Bad creds")

            self.post(wsgi, '/v1/auth/github/authorization', body=body, status=404)

    def test_required_otp(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.side_effect = TwoFactorException(401, 'two factor plz')

            self.post(wsgi, '/v1/auth/github/authorization', body=body, status=401)

    def test_exception(self, wsgi):
        body = {

            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.side_effect = GithubException(500, 'some other exception')

            self.post(wsgi, '/v1/auth/github/authorization', body=body, status=424)

    def test_ok(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)


class TestAuthNGithubToken(DeliTestCase):
    pass


class TestAuthNGithubGeneral(DeliTestCase):
    # These tests will return the same no matter the auth method
    # We are using the authorization method because that was the first
    # method that tests were written for

    def test_not_in_org(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock, \
                patch('github.Organization.Organization') as github_org:
            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'
            github_user.get_orgs.return_value = []

            github_org.has_in_members.return_value = False

            self.post(wsgi, '/v1/auth/github/authorization', body=body, status=403)

    def test_admin_role(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            admin_team = Team(None, [], {"name": "sandwich-admin"}, completed=True)
            admin_team.has_in_members = MagicMock(return_value=True)

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[admin_team])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)

            # TODO: query token for admin role

    def test_unknown_role(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            prefix_team = Team(None, [], {"name": "sandwich-role1"}, completed=True)
            prefix_team.has_in_members = MagicMock(return_value=True)

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[prefix_team])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)

            # TODO: query token for no roles

    def test_prefix_role(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            # TODO: create role role1

            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            prefix_team = Team(None, [], {"name": "sandwich-role1"}, completed=True)
            prefix_team.has_in_members = MagicMock(return_value=True)

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[prefix_team])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)

            # TODO: query token for role role1

    def test_not_in_team(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            prefix_team = Team(None, [], {"name": "sandwich-role1"}, completed=True)
            prefix_team.has_in_members = MagicMock(return_value=False)

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[prefix_team])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)

            # TODO: query token for no roles

    def test_multi_roles(self, wsgi):
        body = {
            'username': fake.word(),
            'password': fake.word()
        }
        with patch('github.AuthenticatedUser.AuthenticatedUser') as github_user_mock:
            # TODO: create role role1

            github_user = github_user_mock.return_value
            github_user.create_authorization.return_value = Authorization(None, [], {"token": "123456789"},
                                                                          completed=True)
            github_user.login = 'user'

            admin_team = Team(None, [], {"name": "sandwich-admin"}, completed=True)
            admin_team.has_in_members = MagicMock(return_value=True)

            prefix_team = Team(None, [], {"name": "sandwich-role1"}, completed=True)
            prefix_team.has_in_members = MagicMock(return_value=True)

            org = Organization(None, [], {"login": "sandwich"}, completed=True)
            org.get_teams = MagicMock(return_value=[admin_team, prefix_team])

            github_user.get_orgs.return_value = [org]

            self.post(wsgi, '/v1/auth/github/authorization', body=body)

            # TODO: query token for admin, role1 roles
