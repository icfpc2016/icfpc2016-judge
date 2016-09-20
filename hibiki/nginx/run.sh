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

set -e

if [[ ! -z "$1" ]]; then
  sed -i "s/localhost:9000/$1/g" /etc/nginx/nginx.conf
fi

graceful_shutdown() {
  nginx -s quit
  wait
  exit $?
}

trap 'graceful_shutdown' TERM

nginx -g 'daemon off;' &
while :; do
  wait
done
