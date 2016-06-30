<%inherit file="base.mako" />\
${request.route_url("account_reset_password", _query={"user_id": user.id, "email_address": email_address, "token": email_token})}
