build-docker:
	docker build -t ci-dashboard:latest .

serve: build-docker
	docker run --rm -it -p 8080:8080 -v "$$PWD"/allowed_slugs.json:/src/allowed_slugs.json -v "$$PWD"/cache:/src/cache -e CIRCLECI_TOKEN="${CIRCLECI_TOKEN}" ci-dashboard:latest -b 0.0.0.0
