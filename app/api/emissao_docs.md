Endpoint: POST /emissao

- Auth: Bearer Token (to be added)
- Payload: `NotfisPayload` defined in `app.schemas.notfis`
- Behavior: Iterates over `documentos` array, validates `cServ`, inserts into `shipments` and `shipment_invoices`.
- Errors: Any exception during processing of a minuta results in an individual failure entry in `data` array and rollback of that minuta's DB transaction.
