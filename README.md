# PoliticianTracker
Website for easily looking up the votes of any politician in the Danish parliament (Folketinget or ft for short)

## Run with Docker
Download this repository and run `make setup` which will download the frontend and backend repos and start up the Docker container which runs the MSSQL database. Then run `make run` to build and start the containers for the frontend (ftweb) and backend (ftdata). The website can then be accessed at `http://localhost:4200`.

## Run locally
Running the services locally still requires the oda-db container with the database. 'ftdata' can be run with `gradle run` from inside its repo, and 'ftweb' with `npm install` followed by `ng serve`. The website can still be accessed at `http://localhost:4200`.

