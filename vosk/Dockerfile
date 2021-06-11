ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8
ENV VOSK_MODEL=en

ARG BASIO_VERSION=0.13.1

RUN wget https://github.com/hassio-addons/bashio/archive/refs/tags/v${BASHIO_VERSION}.tar.gz && \
    tar xzvf v${BASHIO_VERSION}.tar.gz && \
    mv bashio-${BASHIO_VERSION}/lib /usr/lib/bashio && \
    ln -s /usr/lib/bashio/bashio /usr/bin/bashio && \
    rm -rf v${BASHIO_VERSION}.tar.gz bashio-${BASHIO_VERSION} && \
    apt update && apt install -y jq && rm -rf /var/lib/apt/lists

COPY root /

EXPOSE 2700
WORKDIR /opt/vosk-server/websocket
CMD [ "python3", "./asr_server.py", "/opt/vosk-model-${VOSK_MODEL}/model" ]

