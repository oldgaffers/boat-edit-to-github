# boat-edit-to-github
respond to a web hook and create or update a PR for a boat in github

## input body
    {
        "new": { ... },
        "email": "",
        "newItems": { ... }
        "changes": [ ... ]
    }

- new is the full replacement boat register entry.
- email is the email address of the submitter
- newItems is any of builder, designer or design_class as a name and id
- changes is the changes in RFC 6902 JSON Patch format

## output

 a POST to https://api.github.com/repos/oldgaffers/boatregister/actions/workflows/crud.yml/dispatches with the following:

    {
        "ref": "main",
        'inputs': {
            "oga_no": <<OGA number as string>>,
            "new": <<json dump of the incoming newItems>>,
            "data": <<new as a base 64 encoded json dump>>,
            "email": <<email>>,
            "changed_fields": <<changes as a base 64 encoded json dump>>
        }
    }