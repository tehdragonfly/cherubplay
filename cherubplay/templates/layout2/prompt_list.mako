<%inherit file="base.mako" />\
<%block name="title">Your prompts - </%block>
<%block name="body_class">layout2</%block>
<h2>Your prompts</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>Here, you can write your prompts and save them for later. <a href="${request.route_path("new_prompt")}">Write a new prompt</a>.</p>
% if len(prompts)==0:
    <p>You have no prompts.</p>
% else:
    <ul id="chat_list">
% for prompt in prompts:
      <li class="tile2">
        <h3><a href="${request.route_path("prompt", id=prompt.id)}">${prompt.title}</a></h3>
        <p class="subtitle">${prompt_categories[prompt.category]}, ${prompt_levels[prompt.level]}, written ${request.user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
        <p style="color: #${prompt.colour};">\
% if len(prompt.text)>250:
${prompt.text[:250]}...\
% else:
${prompt.text}\
% endif
</p>
      </li>
% endfor
    </ul>
% endif
  </div>
</main>
