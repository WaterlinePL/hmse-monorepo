#!/bin/bash

mc alias set minio https://$ENDPOINT $ACCESS_KEY $SECRET_KEY --api S3v4
for cmd in "$@"
do
  $cmd
  if [ $? -ne 0 ]; then
    echo "Failed command: $cmd"
  fi
done