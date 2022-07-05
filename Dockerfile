FROM quay.io/iotic_labs/iotics-python-base-38:latest AS cert-fetch

RUN \
    apt-get update && \
    apt-get install --no-install-recommends -y wget && \
    wget -q --no-check-certificate -O /corp.iotic.ca.pem https://ca.cor.corp.iotic/ca.pem

# ----------------------------------------------------------------------------------------------------------------------

FROM quay.io/iotic_labs/iotics-python-base-38:latest AS builder

ARG WORKDIR=/ev-charger
ARG PIP_INDEX_URL
RUN test -n "$PIP_INDEX_URL" || (echo "--build-arg PIP_INDEX_URL not set" && false)

ENV \
    SSL_CERT_FILE=/corp.iotic.ca.pem \
    PIP_CERT="$SSL_CERT_FILE"

COPY --from=cert-fetch /corp.iotic.ca.pem "$SSL_CERT_FILE"

WORKDIR $WORKDIR

COPY setup.py setup.cfg "${WORKDIR}/"

RUN \
    pip config set global.trusted-host nexus.cor.corp.iotic && \
    pip install \
        --no-cache-dir \
        --no-compile \
        -e .

COPY bin ./bin
COPY src ./src
COPY entrypoint.sh .ev-demo.prod.seed ./
RUN chmod a+x entrypoint.sh

ENTRYPOINT [ "/ev-charger/entrypoint.sh" ]
