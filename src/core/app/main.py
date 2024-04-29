## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.

#!/usr/bin/env python

# Misc Module Imports
from celery.schedules import crontab
from threading import Lock

# General imports
from app import app

# Celery Imports
from app import celery

import logging, sys

# Set this variable to "threading", "eventlet" or "gevent" to select the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
thread = None
thread_lock = Lock()

def main():
  app.run(app, debug=True)
  logging.basicConfig(stream=sys.stdout, level=logging.INFO)

celery.conf.beat_schedule = {
    'daily_routine_cleaning_backups': {
        'task': 'garbageCollector',
        'schedule': crontab(hour=1, minute=0, day_of_week='*', day_of_month='*', month_of_year='*'),
        'args': ()
    }
}

if __name__ == "__main__":
  main()