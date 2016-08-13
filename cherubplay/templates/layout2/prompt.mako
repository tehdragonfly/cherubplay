<%inherit file="base.mako" />\
<%block name="title">${request.context.title} - </%block>
<%block name="body_class">layout2</%block>
<h2>${request.context.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <section class="tile2">
      <p class="subtitle">${prompt_categories[request.context.category]}, ${prompt_starters[request.context.starter]}, ${prompt_levels[request.context.level]}, written ${request.user.localise_time(request.context.created).strftime("%a %d %b %Y")}.</p>
      <p style="color: #${request.context.colour};">${request.context.text}</p>
      <hr>
      <div class="actions">
        <div class="right"><a href="${request.route_path("edit_prompt", id=request.context.id)}">Edit</a> · <a href="${request.route_path("delete_prompt", id=request.context.id)}">Delete</a></div>
      </div>
    </section>
  </div>
</main>
