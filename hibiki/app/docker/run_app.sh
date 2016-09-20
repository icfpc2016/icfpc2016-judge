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

readonly HEALTH_FILE=/tmp/healthy

graceful_shutdown() {
  #rm -f $HEALTH_FILE
  #sleep 20
  echo q > /tmp/uwsgi-fifo
  wait
  exit $?
}

trap 'graceful_shutdown' TERM

touch $HEALTH_FILE

uwsgi \
  --module=hibiki.wsgi_main:app \
  --lazy-app \
  --disable-logging \
  --uwsgi-socket=:9000 \
  --master \
  --workers=$(( $(nproc) * 2 )) \
  --threads=64 \
  --master-fifo=/tmp/uwsgi-fifo \
  "$@" &

while :; do
  wait
done
