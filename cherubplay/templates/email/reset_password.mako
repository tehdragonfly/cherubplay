<%inherit file="base.mako" />\
  <h2 style="margin: 50px 50px 20px; color: #090; font-size: 2em; text-align: center; line-height: normal; text-transform: uppercase;">Reset your password</h2>
  <div style="box-sizing: border-box; max-width: 650px; margin: 20px auto; padding: 20px 25px; background-color: #fff; box-shadow: 0 1px 2px #bbb;">
     <p style="margin-top: 0;">If you've forgotten your password, please <a style="color: #090;" href="${request.route_url("account_reset_password", _scheme="https", _query={"user_id": user.id, "email_address": email_address, "token": email_token})}">click here</a> to reset it.</p>
    <p style="margin-bottom: 0;">This link will expire in 1 hour.</p>
  </div>
