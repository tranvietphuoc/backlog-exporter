#! /bin/bash

gunicorn run:app -w 1 --log-file -
