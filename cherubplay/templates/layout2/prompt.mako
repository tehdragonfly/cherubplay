<%inherit file="base.mako" />\
<%block name="title">${request.context.title} - </%block>
<%block name="body_class">layout2</%block>
<% from cherubplay.lib import prompt_categories, prompt_starters, prompt_levels %>
<h2>${request.context.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <section class="tile2">
      <p class="subtitle">${prompt_categories[request.context.category] if request.context.category else "<span class=\"error\">Category not set</span>"|n}, ${prompt_starters[request.context.starter]}, ${prompt_levels[request.context.level]}, written ${request.user.localise_time(request.context.created).strftime("%a %d %b %Y")}.</p>
      <div class="message" style="color: #${request.context.colour};">${request.context.text.as_html()}</div>
      <hr>
      <div class="actions">
        <div class="right"><a href="${request.route_path("edit_prompt", id=request.context.id)}">Edit</a> · <a href="${request.route_path("delete_prompt", id=request.context.id)}">Delete</a></div>
      </div>
    </section>
  </div>
</main>
