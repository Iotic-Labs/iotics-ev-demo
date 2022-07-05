# TODO

- update to the latest id sdk for the python code
- update the id sdk for javascript: compile to `wasm` and re-write the wrapper.
- update to grpc instead of rest
- model the demo following up the ecosystem
  - currently we have "publisher" "subscriber" and "observer" and the roles are discussed during the demo
  - it should be better to have "car", "station manager", "ev point manufacturer", "third party service provider" and run the demo from their perspective
  - use at least two spaces
- use a proper ontology for ev charging
  - https://www.maxime-lefrancois.info/docs/LefrancoisHabaultRamondouFrancon-GREEN16-Outsourcing.pdf
  - https://comune-milano.github.io/ontologie-iot-urbani/docs/electric/index-en.html
  - https://github.com/mhg-local/sargon
- for our custom ontology, deploy it in data.iotics.com
- make it flow with the presentation https://docs.google.com/presentation/d/1rm3lnTjLqg1CN3Cp63LmmMFcWGVwsxmVtCk7NlFeaqE/edit#slide=id.gb84b1d82b0_0_3
- make it so that it forms a codebase that devs can refer to.
- dashboards in portal

## WHAT / WHY and HOW < your benefit>

- how do surface/demonstrate the following IOTICS value propositions  
  - decentralisation / self sovreignty
  - symmetry: everything needs to be a twin
    - roles: follower, publisher, synthesiser
  - selective data sharing / brokered interactions
  - what is a digital twin
    - metadata of the underlying asset
      - schema for ontology < show how to use common model
    - behaviour of the twin in the agent
    - identity
  - autonomous interoperability




- showcase identity decentralisation
  - build the chrome browser extension to work as a "wallet"
  - inject jwt token in the js instead of having to do it via login
- separate the ML in its own process to demonstrate the ecosystem 3rd party

  ============
  outside in view of iotics <observer>  <analytics>   <graphy>    
  inside out view <car>                 <operatioal>  <streaming>