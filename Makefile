.PHONY: setup
setup:
	git clone https://github.com/Hagen10/ftweb.git
	git clone https://github.com/Hagen10/ftweb-rb.git
	git clone https://github.com/Hagen10/ftdata.git
	docker-compose --profile core up --build -d

.PHONY: run-ts
run-ts:
	docker-compose --profile ftdata --profile ftweb-ts up --build -d

.PHONY: stop-ts
stop-ts:
	docker-compose --profile ftdata --profile ftweb-ts stop

.PHONY: run-rb
run-rb:
	docker-compose --profile ftdata --profile ftweb-rb up --build -d

.PHONY: stop-rb
stop-rb:
	docker-compose --profile ftdata --profile ftweb-rb stop


.PHONY: stop-all
stop-all:
	docker-compose --profile core --profile ftdata --profile ftweb-ts --profile ftweb-rb down

.PHONY: clean
clean:
	rm -rf ftweb ftdata	ftweb-rb