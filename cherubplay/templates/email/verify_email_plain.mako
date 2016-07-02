Before we can change your e-mail address, we need to verify that it's really you.

Please visit the following URL to verify your e-mail address: ${request.route_url("account_verify_email", _scheme="https", _query={"user_id": user.id, "email_address": email_address, "token": email_token})}
