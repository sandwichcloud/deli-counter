#!/usr/bin/env bash

curl -H "Content-Type: application/json" -d "{\"source_type\": \"Tag\", \"source_name\": \"$TRAVIS_TAG\"}" -X POST "$DOCKER_HUB_TRIGGER"