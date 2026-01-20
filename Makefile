.PHONY: setup
setup:
	git clone https://github.com/Hagen10/ftweb.git
	git clone https://github.com/Hagen10/ftdata.git
	docker-compose --profile core up --build -d

.PHONY: run
run:
	docker-compose --profile app up --build -d

.PHONY: stop
stop:
	docker-compose --profile app stop

.PHONY: stop-all
stop-all:
	docker-compose --profile core --profile app down

.PHONY: clean
clean:
	rm -rf ftweb ftdata	