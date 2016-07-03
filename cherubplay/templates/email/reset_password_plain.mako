If you've forgotten your password, please visit the following URL to reset it: ${request.route_url("account_reset_password", _scheme="https", _query={"user_id": user.id, "email_address": email_address, "token": email_token})}

This link will expire in 1 hour.
