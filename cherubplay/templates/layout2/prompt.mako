<%inherit file="base.mako" />\
<%block name="title">${prompt.title} - </%block>
<%block name="body_class">layout2</%block>
<h2>${prompt.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <section class="tile2">
      <p class="subtitle">${prompt_categories[prompt.category]}, ${prompt_levels[prompt.level]}, written ${request.user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
      <p style="color: #${prompt.colour};">${prompt.text}</p>
      <hr>
      <p><a href="${request.route_path("edit_prompt", id=prompt.id)}">Edit</a></p>
    </section>
  </div>
</main>
