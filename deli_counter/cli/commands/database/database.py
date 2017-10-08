from clify.command import Command

from deli_counter.cli.commands.database.current import CurrentCommand
from deli_counter.cli.commands.database.downgrade import DowngradeCommand
from deli_counter.cli.commands.database.history import HistoryCommand
from deli_counter.cli.commands.database.revision import RevisionCommand
from deli_counter.cli.commands.database.upgrade import UpgradeCommand
from ingredients_db.database import Database
from ingredients_http.conf.loader import SETTINGS


class DatabaseCommand(Command):
    def __init__(self):
        super().__init__('database', 'Deli Counter Database Commands')
        self.database = None

    def setup_arguments(self, parser):
        pass

    def add_subcommands(self):
        CurrentCommand().register_subcommand(self)
        UpgradeCommand().register_subcommand(self)
        DowngradeCommand().register_subcommand(self)
        HistoryCommand().register_subcommand(self)
        RevisionCommand().register_subcommand(self)

    def setup(self, args):
        self.database = Database(SETTINGS.DATABASE_HOST, SETTINGS.DATABASE_PORT, SETTINGS.DATABASE_USERNAME,
                                 SETTINGS.DATABASE_PASSWORD, SETTINGS.DATABASE_DB, SETTINGS.DATABASE_POOL_SIZE,
                                 migration_scripts_location='ingredients_db:alembic')
        self.database.connect()
        return 0

    def run(self, args) -> int:
        self.logger.error("How did you get here?")
        return 1
