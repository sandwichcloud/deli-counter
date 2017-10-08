import secrets

from ingredients_db.models.user import User, UserToken


def generate_oauth_token(session, username: str) -> UserToken:
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        user = User()
        user.username = username
        session.add(user)
        session.flush()

    token = UserToken()
    token.user_id = user.id
    token.access_token = secrets.token_urlsafe()
    session.add(token)

    return token
