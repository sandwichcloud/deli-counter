import os


def main():
    os.environ['CLI'] = 'true'
    os.environ['settings'] = 'deli_counter.settings'
    from deli_counter.cli.app import DeliApplication
    from deli_counter.cli.commands.database.database import DatabaseCommand

    app = DeliApplication()
    app.register_command(DatabaseCommand())
    app.run()
