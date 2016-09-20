# Copyright 2016 ICFP Programming Contest 2016 Organizers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DEVSERVER_ARGS ?=

.PHONY: default force clean distclean devserver dev prod

default: devserver

force:

clean:
	rm -rf build/dev build/prod

distclean:
	rm -rf build

devserver: dev devpython
	cd build/dev && PATH=$$PWD/../python/bin:$$PATH PYTHONPATH=$$PWD python hibiki/devserver_main.py $(DEVSERVER_ARGS)

devpython: build/python/.stamp

dev: build/dev/.stamp

prod: build/prod/.stamp


build/dev/.stamp: build/dev/hibiki build/dev/static build/dev/akatsuki build/dev/requirements.txt
	touch $@

build/dev/hibiki:
	mkdir -p `dirname $@`
	ln -s ../../hibiki $@

build/dev/static:
	mkdir -p `dirname $@`
	ln -s ../../static $@

build/dev/akatsuki: prebuilts/akatsuki
	mkdir -p `dirname $@`
	ln -s ../../prebuilts/akatsuki $@

build/dev/requirements.txt:
	mkdir -p `dirname $@`
	ln -s ../../requirements.txt $@

build/python/.stamp: requirements.txt
	[ -d build/python ] || virtualenv build/python
	build/python/bin/pip install -r requirements.txt
	touch $@

build/prod/.stamp: build/dev/.stamp $(shell find -L build/dev) $(shell find docker)
	mkdir -p `dirname $@`
	rsync -rpLt --delete --exclude='.*' --exclude='*.pyc' build/dev/ build/prod/
	rsync -rpLt --include='.dockerignore' --exclude='.*' docker/ build/prod/
	touch $@
