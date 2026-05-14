.PHONY: setup
setup:
	test -d ftweb    || git clone https://github.com/Hagen10/ftweb.git
	test -d ftweb-rb || git clone https://github.com/Hagen10/ftweb-rb.git
	test -d ftdata   || git clone https://github.com/Hagen10/ftdata.git
	docker compose --profile core up --build -d

.PHONY: download-data
download-data:
	bash scripts/download-ft-helemoedet.sh _data $(ARGS)

.PHONY: run-ts
run-ts:
	docker compose --profile ftdata --profile ftweb-ts up --build -d

.PHONY: stop-ts
stop-ts:
	docker compose --profile ftdata --profile ftweb-ts stop

.PHONY: run-rb
run-rb:
	docker compose --profile ftdata --profile ftweb-rb up --build -d

.PHONY: stop-rb
stop-rb:
	docker compose --profile ftdata --profile ftweb-rb stop
	
.PHONY: run-vector
run-vector:
	mkdir -p ftdata/vectors/models
	docker compose --profile vector up --build -d

.PHONY: stop-vector
stop-vector:
	docker compose --profile vector stop

.PHONY: stop-all
stop-all:
	docker compose --profile core --profile ftdata --profile ftweb-ts --profile ftweb-rb --profile vector down

.PHONY: clean
clean:
	rm -rf ftweb ftdata	ftweb-rb