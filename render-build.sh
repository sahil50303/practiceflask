#!/usr/bin/env bash
set -e

# Install required dependencies
apt-get update
apt-get install -y curl apt-transport-https gnupg

# Microsoft ODBC Driver 17 for SQL Server
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev
