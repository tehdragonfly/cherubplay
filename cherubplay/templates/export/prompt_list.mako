<% from cherubplay.lib import prompt_categories, prompt_starters, prompt_levels %>
<!DOCTYPE html>
<html>
<head>
<title>Your prompts - Cherubplay</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#393">
<link rel="stylesheet" href="../cherubplay2.css">
</head>
<body class="layout2">

<header>
  <h1><img src="../logo.png" alt="Cherubplay"></h1>
</header>

<h2>Your prompts</h2>

<main class="flex">
  <div id="content">
  % if len(prompts) == 0:
    <p>You have no prompts.</p>
  % else:
    <ul id="chat_list">
    % for prompt in prompts:
      <li class="tile2">
        <h3><a href="${prompt.id}.html">${prompt.title}</a></h3>
        <p class="subtitle">${prompt_categories[prompt.category] if prompt.category else "<span class=\"error\">Category not set</span>"|n}, ${prompt_starters[prompt.starter]}, ${prompt_levels[prompt.level]}, written ${user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
        <% was_trimmed, preview_text = prompt.text.trim_html(250) %>
        <div class="message" style="color: #${prompt.colour};">${preview_text}</div>
      </li>
    % endfor
    </ul>
  % endif
  </div>
</main>

</body>
</html>