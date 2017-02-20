<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">\
% if request.matched_route.name == "directory_request_edit":
Edit request #${request.context.id}
% else:
New request
% endif
</%block>
    <form id="new_request_form" class="tile2" action="${request.current_route_path()}" method="post">
      <p><label>Maturity: <select name="maturity" required>
        % if request.matched_route.name != "directory_request_edit":
        <option value=""></option>
        % endif
        % for maturity in Tag.maturity_names:
        <option${" selected" if form_data.get("maturity") == maturity else ""}>${maturity}</option>
        % endfor
      </select> (<a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">Category rules</a>)</label></p>
      % if error == "blank_maturity":
      <p class="error">Please choose a maturity for your prompt.</p>
      % endif
      <label>Content warnings:</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="warning" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("warning", "")}">
      </div>
      <p class="help">Content warnings must include anything that belongs under NSFW extreme.</p>
      <p class="types">
        <span>Type:</span>
        % for tag_type in Tag.type_names:
        <label><input type="checkbox" name="type_${tag_type}"${" checked" if "type_" + tag_type in form_data else ""}> ${tag_type}</label>
        % endfor
      </p>
      <hr>
      <h3>Who you're playing</h3>
      <label>Fandom(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="fandom" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("fandom", "Homestuck")}">
      </div>
      <label>Character(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="character" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("character", "")}">
      </div>
      <label>Gender(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="gender" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("gender", "")}">
      </div>
      <hr>
      <h3>Who you're looking for</h3>
      <label>Fandom(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="fandom_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("fandom_wanted", "Homestuck")}">
      </div>
      <label>Character(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="character_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("character_wanted", "")}">
      </div>
      <label>Gender(s):</label>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="gender_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("gender_wanted", "")}">
      </div>
      <hr>
      <h3>Other tags</h3>
      <p class="help">Other tags can contain anything else you think is relevant - AUs, kinks and the like.</p>
      <div class="tag_input">
        <ul class="request_tags"></ul>
        <input type="text" class="full" name="misc" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("misc", "")}">
      </div>
      <hr>
      <h3>OOC notes</h3>
      <p><textarea name="ooc_notes" placeholder="Enter your OOC notes...">${form_data.get("ooc_notes", "")}</textarea></p>
      % if error == "blank_ooc_notes_and_starter":
      <p class="error">Please write some notes and/or a starter.</p>
      % endif
      <hr>
      <h3>Starter</h3>
      <p class="help">If your request doesn't have a starter (eg. if it's a request without any prose, a missed connection or a MSPARP group), please leave this section blank and write everything in the OOC notes section. It'll then automatically be tagged as <a href="${request.route_path("directory_tag", tag_string="type:No_starter")}" target="_blank">type:No starter</a>.</p>
      <p><input type="color" name="colour" size="6" maxlength="7" value="${form_data.get("colour") or "#000000"}"> <select name="preset_colours">
        % for hex, name in preset_colours:
        <option value="#${hex}">${name}</option>
        % endfor
      </select></p>
      % if error == "invalid_colour":
      <p class="error">Invalid text colour. The colour needs to be a 6-digit hex code.</p>
      % endif
      <p><textarea name="starter" placeholder="Enter your starter..." style="color: ${form_data.get("colour") or "#000000"}">${form_data.get("starter", "")}</textarea></p>
      <hr>
      <div class="actions">
        <div class="right"><input type="submit" name="draft" value="Save draft"> · <input type="submit" name="publish" value="Publish"></div>
      </div>
    </form>
<%block name="scripts">
${parent.scripts()}
<script>cherubplay.directory_new();</script>
</%block>
