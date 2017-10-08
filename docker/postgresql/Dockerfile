FROM postgres:alpine

ADD docker/postgresql/createPostgresExtension.sh /docker-entrypoint-initdb.d/
RUN chmod 755 /docker-entrypoint-initdb.d/createPostgresExtension.sh