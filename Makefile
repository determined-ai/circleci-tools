build-docker:
	docker build -t ci-dashboard:latest .

serve: build-docker
	docker run --rm -it -p 9999:9999 -v "$$PWD"/cache:/src/cache -e CIRCLECI_TOKEN="${CIRCLECI_TOKEN}" ci-dashboard:latest -b 0.0.0.0
