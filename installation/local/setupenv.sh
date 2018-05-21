#!/bin/bash

### 
### Set up proper environment variables for use with das snitch
###

#Default values
projectid=22354

WARN='\033[0;31m'
NOCOLOR='\033[0m'
if [ "$0" == "$BASH_SOURCE" ]; then
    echo "Must be sourced, not run interactively."
    exit 1
fi

read -p "Enter Password Safe Project ID (just hit enter for default: $projectid): " PWSAFE_PROJECT && [[ -z "$PWSAFE_PROJECT" ]] && PWSAFE_PROJECT="$projectid"
read -p "Enter SSO User: " SSO_USERNAME && [[ -z "$SSO_USERNAME" ]] && printf "${WARN}WARNING:${NOCOLOR} Username cannot be empty."
read -p "Enter SSO Password: " -s SSO_PASSWORD && [[ -z "$SSO_PASSWORD" ]] && printf "${WARN}WARNING:${NOCOLOR} Password cannot be empty."
echo ""

export SSO_USERNAME SSO_PASSWORD PWSAFE_PROJECT
