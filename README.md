# PoliticianTracker
Website for easily looking up the votes of any politician in the Danish parliament (Folketinget or ft for short)

## Run with Docker
Download this repository and run `make setup` which will download the frontend and backend repos and start up the Docker container which runs the MSSQL database. Then run `make run` to build and start the containers for the frontend (ftweb) and backend (ftdata). The website can then be accessed at `http://localhost:4200`.

## Run locally
Running the services locally still requires the oda-db container with the database. 'ftdata' can be run with `gradle run` from inside its repo, and 'ftweb' with `npm install` followed by `ng serve`. The website will still be accessed at `http://localhost:4200`.

## To-Do

### ftdata
- What could be nice is to somehow compare the newest downloaded database with the previous one to ensure that data isn't all of a sudden lost.
- some type of authentication between frontend and backend?
- harden security wise. Should the communication between frontend and backend be mtls? Likely. Also, the application.yml file should be fed the password instead of hardcoding. Applies anywhere where the password is appearing at present.
- create a new repo for the frontend written in Typescript
- testing?
- remove all hardcoded passwords

### ftweb
- The api URL to ftdata still uses regular http...
- search bar to quickly locate the right politician is a must
- I suppose we need some data clean up so these admins and test entries don't appear. Do they have all the same relations with other tables as the actual politicians do?
- It should also be possible to search for party and then only show party members. We need to retrieve the bio and retrieve party with regex I think. Doesn't seem like there's any other table that contains that information.
- Not sure if the Person interface should be located elsewhere than Overview now that the Politician component also uses it. Maybe it should be moved to Apiservice so we can get rid of Observable<any> type.
- what happens if the politician id is not a valid one? we should display something like a notification
- Add virtual scrolling for better performance
- It should show just whether it was passed or rejected, then the conclusion summary could show if you hover over it.
- fix css for politician.html
- Look into deferred views for the politician vote list, maybe a small loading message would be nice.