<%inherit file="base.mako" />\
<%block name="title">New prompt - </%block>
<%block name="body_class">layout2</%block>
<h2>New prompt</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <form class="tile2" action="${request.route_path("new_prompt")}" method="post">
      <h3><input type="text" id="prompt_title" name="prompt_title" placeholder="Title..." maxlength="100" required value="${request.POST.get("prompt_title", "")}"></h3>
% if error == "blank_title":
      <p class="error">Prompt title can't be empty.</p>
% endif
      <p><input type="color" id="prompt_colour" name="prompt_colour" size="6" maxlength="7" value="${request.POST.get("prompt_colour") or "#000000"}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
        <option value="#${hex}">${name}</option>
% endfor
      </select></p>
% if error == "invalid_colour":
      <p class="error">Invalid text colour. The colour needs to be a 6-digit hex code.</p>
% endif
      <p><textarea id="prompt_text" name="prompt_text" placeholder="Enter your prompt..." required>${request.POST.get("prompt_text", "")}</textarea></p>
% if error == "blank_text":
      <p class="error">Prompt text can't be empty.</p>
% endif
      <div id="prompt_dropdowns">Post to:
        <select id="prompt_category" name="prompt_category" required>
          <option value="">Category...</option>
% for id, name in prompt_categories.items():
          <option value="${id}">${name}</option>
% endfor
        </select>
        <select id="prompt_level" name="prompt_level" required>
          <option value="">Level...</option>
% for id, name in prompt_levels.items():
          <option value="${id}">${name}</option>
% endfor
        </select>
        (<a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">?</a>)
      </div>
% if error == "blank_category":
      <p class="error">Please choose a category for your prompt.</p>
% elif error == "blank_level":
      <p class="error">Please choose a level for your prompt.</p>
% endif
      <hr>
      <button type="submit" id="post_button">Save</button>
      <br class="clear">
    </form>
  </div>
</main>
