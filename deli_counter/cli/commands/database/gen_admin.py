import secrets

from clify.command import Command

from ingredients_db.models.builtin import BuiltInUser


class GenAdminCommand(Command):
    def __init__(self):
        super().__init__('gen-admin', 'Creates an admin account in the builtin auth driver')

    def setup_arguments(self, parser):
        pass

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        with self.parent.database.session() as session:
            user = session.query(BuiltInUser).first()
            if user is not None:
                self.logger.error("Users already exist, cannot create admin account.")
                return 1

            password = secrets.token_urlsafe()

            user = BuiltInUser()
            user.username = 'admin'
            user.password = password
            user.roles = ["admin"]
            session.add(user)
            session.commit()
            session.refresh(user)

            self.logger.info("Created an admin account with the password of " + password)
        return 0
