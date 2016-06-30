<%inherit file="base.mako" />\
  <h2 style="margin: 50px 50px 20px; color: #090; font-size: 2em; text-align: center; line-height: normal; text-transform: uppercase;">Verify your e-mail address</h2>
  <div style="box-sizing: border-box; max-width: 650px; margin: 20px auto; padding: 20px 25px; background-color: #fff; box-shadow: 0 1px 2px #bbb;">
    <p style="margin-top: 0;">Before we can change your e-mail address, we need to verify that it's really you.</p>
    <p style="margin-bottom: 0;">Please <a style="color: #090;" href="${request.route_url("account_verify_email", _query={"user_id": user.id, "email_address": email_address, "token": email_token})}">click here</a> to verify your e-mail address.</p>
  </div>
