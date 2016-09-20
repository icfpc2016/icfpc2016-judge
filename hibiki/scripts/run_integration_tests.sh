#!/bin/bash
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

make -C app prod || exit $?

sudo docker build -t hibiki-app:test app/build/prod || exit $?
sudo docker build -t hibiki-nginx:test nginx || exit $?

sudo docker-compose -f compose/test.yaml -p hibikitest kill
sudo docker-compose -f compose/test.yaml -p hibikitest down --remove-orphans --volumes

if ! sudo docker-compose -f compose/test.yaml -p hibikitest up -d --timeout 3 --remove-orphans; then
  echo "Failed to bring up test servers."
  exit 1
fi

make -C app devpython || exit $?

app/build/python/bin/python -m nose -w app/tests
ret=$?
echo

sudo docker-compose -f compose/test.yaml -p hibikitest kill

if [[ $ret = 0 ]]; then
  echo "PASSED!"
  sudo docker-compose -f compose/test.yaml -p hibikitest down --remove-orphans --volumes
else
  echo "Integration tests failed."
  echo "Run the following command to see app logs:"
  echo "$ sudo docker logs hibikitest_app_1"
  echo
fi

exit $ret
