from clify.command import Command
from simple_settings import settings

from deli_counter.cli.commands.database.current import CurrentCommand
from deli_counter.cli.commands.database.downgrade import DowngradeCommand
from deli_counter.cli.commands.database.gen_admin import GenAdminCommand
from deli_counter.cli.commands.database.history import HistoryCommand
from deli_counter.cli.commands.database.revision import RevisionCommand
from deli_counter.cli.commands.database.upgrade import UpgradeCommand
from ingredients_db.database import Database


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
        GenAdminCommand().register_subcommand(self)

    def setup(self, args):
        self.database = Database(settings.DATABASE_HOST, settings.DATABASE_PORT, settings.DATABASE_USERNAME,
                                 settings.DATABASE_PASSWORD, settings.DATABASE_DB, settings.DATABASE_POOL_SIZE,
                                 migration_scripts_location='ingredients_db:alembic')
        self.database.connect()
        return 0

    def run(self, args) -> int:
        self.logger.error("How did you get here?")
        return 1
