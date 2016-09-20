#!/bin/bash -e
#
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

cd "$(dirname "$0")/.."

start() {
  scripts/run_integration_tests.sh
  for i in app nginx; do
    sudo docker tag hibiki-$i:test hibiki-$i:extended
  done
  sudo docker-compose -f compose/extended.yaml -p hibiki up -d --remove-orphans
}

stop() {
  sudo docker-compose -f compose/extended.yaml -p hibiki stop
}

clean() {
  sudo docker-compose -f compose/extended.yaml -p hibiki down --remove-orphans --volumes
}

case "$1" in
start) start;;
stop) stop;;
clean) clean;;
*)
  echo "usage: $0 <start|stop|clean>"
  exit 1
esac
