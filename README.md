# PoliticianTracker
Website for easily looking up the votes of any politician in the Danish parliament (Folketinget or ft for short). It relies on 2 repos, the first being ftdata which sets up a container with the mssql database and a Kotlin application responsible for queries. ftdata also exposes an api which another application can use to retrieve data from the database. The 2nd repo is either ftweb (Typescript/Angular to be removed) or ftweb-rb (ruby on rails) which both retrieves data from ftdata and then displays it on a webpage. The reason why there is both a typescript/angular and a ruby on rails repo for the frontend is that the project was started with typescript but a decision was made to learn ruby instead, so as the ruby repository advances, the typescript repo will not. It is scheduled for deletion.

## Run with Docker
### Prerequisites
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose plugin](https://docs.docker.com/compose/install/linux/) (`docker compose version`)
- [Docker Buildx plugin](https://github.com/docker/buildx/releases) (`docker buildx version`)

Download this repository and run `make setup` which will download the frontend and backend repos and start up the Docker container which runs the MSSQL database. Then run `make run-ts` to build and start the containers for the frontend (ftweb typescript) and backend (ftdata) or `make run-rb` for running the setup with the ruby on rails container. The website can then be accessed at `http://localhost:4200` (use port `3000` for ruby on rails).

## Run locally
Running the services locally still requires the oda-db container with the database. 'ftdata' can be run with `gradle run` from inside its repo. 'ftweb' can be run with `npm install` followed by `ng serve` or instead 'ftweb-rb' can be run with `bin/rails server`. All of these commands are to be run from within their respective directory. The website will still be accessible at `http://localhost:4200` (use port `3000` for ruby on rails).

## Vector embeddings
The main branch of the `ftdata`repository now contains dockerfiles to set up a small vector embedding generation and retrieval environment. Run `make run-vector` to set it up here. More info can be found in the `README.md` file found in the `ftdata` directory.

## To-Do

### ftdata
- What could be nice is to somehow compare the newest downloaded database with the previous one to ensure that data isn't all of a sudden lost.
- some type of authentication between frontend and backend?
- harden security wise. Should the communication between frontend and backend be mtls? Likely. Also, the application.yml file should be fed the password instead of hardcoding. Applies anywhere where the password is appearing at present.
- testing?
- remove all hardcoded passwords
- queries should probably include period, so we can filter voting sessions by year or parliamentary year in the UI

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

### ftweb-rb
- clean up all the folders and files not needed.
- Security?
- Look into kamal

### Other things
- make a way to back up the volume of the solr index
- Currently we are also indexing all the "Spørgeren" and "Ordføreren" words. We can remove those. Example when searching for "drone":
Leif Lahn Jensen - 2025-10-09T10:13:12Z
Spørgeren.
Leif Lahn Jensen - 2025-10-09T10:16:31Z
Spørgeren.
Leif Lahn Jensen - 2025-10-09T10:19:17Z
Spørgeren.
Søren Gade - 2025-10-09T11:54:41Z
Spørgeren.
Søren Gade - 2025-10-09T11:58:18Z
Spørgeren.
Lars-Christian Brask - 2025-10-09T12:43:31Z
Spørgeren.
Lars-Christian Brask - 2025-10-09T12:47:08Z
Spørgeren.
Lars-Christian Brask - 2025-10-09T12:50:34Z
Spørgeren. 

## Update
- signed signatures are being enforced

## 30 AUG 2026 - NOTE
The gratitude_time.py calculates the gratitude time by dividing the total talk time of the talesegment with (gratitude_words / total_talesegment_words). I think that's generally quite a good way to do it, but I wonder if there's room for optimization? If a Politician stutters and takes long breaks saying "uhm" etc. maybe the total talk time is very long without a large total word count. In that case "tak til ordføreren" will come off as having taken longer to say through this calculation