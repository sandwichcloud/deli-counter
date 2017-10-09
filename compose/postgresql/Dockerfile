FROM postgres:alpine

ADD compose/postgresql/createPostgresExtension.sh /compose-entrypoint-initdb.d/
RUN chmod 755 /compose-entrypoint-initdb.d/createPostgresExtension.sh