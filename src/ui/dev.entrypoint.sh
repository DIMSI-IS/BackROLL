#!/bin/bash

# Loading environment files in accordance with the dependency order.
source load_env.sh .env.tmpl

# Starting the web app.
npm run serve
