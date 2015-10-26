<%inherit file="base.mako" />\
<%block name="title">Delete ${prompt.title} - </%block>
<%block name="body_class">layout2</%block>
<h2>Delete ${prompt.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>Are you sure you want to delete this prompt?</p>
    <section class="tile2">
      <p class="subtitle">${prompt_categories[prompt.category]}, ${prompt_levels[prompt.level]}, written ${request.user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
      <p style="color: #${prompt.colour};">${prompt.text}</p>
    </section>
    <form action="${request.route_path("delete_prompt", id=prompt.id)}" method="post">
      <p><button type="submit">Delete prompt</button></p>
    </form>
  </div>
</main>
