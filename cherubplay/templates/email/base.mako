<!DOCTYPE html>
<html>
<head>
<title>Cherubplay</title>
</head>
<body style="margin: 0; padding: 1px; background-color: #eee; font-family: sans-serif; line-height: 1.5em;">

<div style="background-color: #393;">
  <h1 style="margin: 0; padding: 10px; color: #fff;">
    <a style="display: block; max-width: 565px; margin: 0 auto;" href="${request.route_url("home", _scheme="https")}">
      <img style="display: block; max-width: 100%; margin: 0 auto;" src="${request.route_url("home", _scheme="https")}static/logo.png" alt="Cherubplay">
    </a>
  </h1>
</div>

<div style="margin: 50px;">
${next.body()}\
</div>

</body>
</html>

