# DEMO: EV charging stations

## Overview

This demo implements the following use case. A set of Electric vehicle charger located around the country are represented as digital twins.
Each charging station has one or more connections also represented as digital twins.

Users of the system want to search for operational charging stations of the type compatible with their own vehicle, for the purpose of checking whether any of their connections are free within 1 or 2 hours. Availability at 1 or 2 h is expressed as a probability number between 0 and 1, with 0 meaning certainly not available and 1 meaning certainly available.

Operational status is updated every hour and available as charging station or connection metadata or feed. Forecast at 1 or 2 h is available as as a feed on the connection digital twin.

## Build and run

`make setup` to initialise the python env and download dependencies
`make gen` to generate gRPC binding code

`make CMD=src/<app> <target>` runs `<app>` agent on the space defined in the `<target>` Makefile target.

For example: `make CMD=src/twin_manager.py run-demo`

## Purpose

The purpose of this demo is to showcase some of the IOTICS concepts and how to implement an application that leverages IOTICS unique value.

### Architecture

![Architecture](https://github.com/Iotic-Labs/iotics-ev-demo/blob/import/architecture.png?raw=true)

### The IOTICS "digital twin"

A digital twin in IOTICS is:

- Metadata describing the underlying asset, store in IOTICS. The IOTICS Web API allows the creation, deletion, update and list of the twins' properties.
- the agent _program_ that bridges the real device or data source. This is the program that constitutes the "brain" of the twin that keeps the virtual and the real in sync. The agent program itself has an Identity.
- the Identity of the twin: in IOTICS twins have an identity, represented by the combination of a DiD and its respective DiD document. (more on this)

The _program_ is an abstract concept that refers to a set of instructions that manage the specific twin<>device interactions. In practice this program can be a standalone application or an application that manages multiple twins; in this case the program is more akin to a thread of execution that logically maps to a twin.
In IOTICS _programs_ that manage multiple twins are addressed as _connectors_. All programs in the src/ directory are connectors that manage one or more twins.

### The demo code

The demo code is made of

- a "twin manager" application that acts as an agent for a set of charging stations and points; it maintains the model in code and keeps twins and real counterparts (charging stations and connectors) in sync
- an observer representing an application doing analytics on the knowledge graph
- a subscriber representing an application finding and binding twins in the network
- a browser based app with search, find and bind: this - like the subscriber - shows find and bind, plus a mechanism to directly use the REST/STOMP apis and showcase how one can write jamstack architectures entirely driven by metadata.
- an "ai algorithm" developed by an external operator. This represents the use case where a third party company re-uses data in IOTICS to provide added value services. In this case, an AI algo that works out occupancy of the charging stations.
- a "follower" app that stores data in an elasticsearch datastore for further analytics via kibana.


### The symmetry between producer and consumer

Symmetry between producer and consumer is implemented in IOTICS. This is shown by having the subscriber app representing itself as a twin.
Note that the observer isn't symmetrical as such (access to metadata is not governed by brokered interactions)

### The separation between metadata and data

Show how data is modelled in code and how data is published. This is shown in code in the publisher (two sections one for modeling and another for sharing). It's also possible to show that observer works even if publisher isn't running

### Finding and binding to twins

Search by text and metadata - Subscriber shows this quite clearly; the browser based app too. Search + parsing of metadata and feeds to decide whether one may want to bind to a feed or not. (we don't have feed semantic metadata - this sucks!)

### Driving the application logic from metadata

Rendering of the UI from the metadata. Browser app does it (almost) quite well... the tables are rendered entirely based on data coming from the server. we don't do meta analysis (ie we don't match on actual predicates but we could quite easily)

### The IOTICS Identity and security model

See the device demo

### Other concerns

Twin as an aggregation of multiple systems: we have the EV APIs and the AI doing the forecast, aggregated in a twin.

---

TBC