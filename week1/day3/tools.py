TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_package",
            "description": "Check the status and details of a package by its ID. Returns package info including contents, destination, and security code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "packageid": {
                        "type": "string",
                        "description": "The package ID to look up",
                    }
                },
                "required": ["packageid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redirect_package",
            "description": "Redirect a package to a new destination. Requires the package ID, new destination code, and authorization/security code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "packageid": {
                        "type": "string",
                        "description": "The package ID to redirect",
                    },
                    "destination": {
                        "type": "string",
                        "description": "The new destination code",
                    },
                    "code": {
                        "type": "string",
                        "description": "The security/authorization code for the package",
                    },
                },
                "required": ["packageid", "destination", "code"],
            },
        },
    },
]