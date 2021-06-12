#!/usr/bin/env bashio

/etc/cont-init.d/01-install-models

bashio::log.info "Preparing to run Vosk"

LANGUAGE=$(bashio::config "language[0]")
[ -z "$LANGUAGE" ] && LANGUAGE=en

python3 /asr_server.py -vv /data/vosk-model/${LANGUAGE}
