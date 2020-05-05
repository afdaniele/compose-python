ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PART=patch

new-dist:
	$(MAKE) clean bump-upload

bump-upload:
	$(MAKE) bump upload

bump:
	bumpversion ${PART}

upload:
	git push --tags
	git push
	$(MAKE) clean
	$(MAKE) build
	twine upload dist/*

build:
	python3 setup.py sdist

clean:
	rm -rf dist/ build/ compose_cms.egg-info/

format:
	yapf -r -i -p -vv ${ROOT_DIR}