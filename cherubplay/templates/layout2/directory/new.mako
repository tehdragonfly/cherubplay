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
      <p><label><select name="maturity">
        % for maturity in Tag.maturity_names:
        <option${" selected" if form_data.get("maturity") == maturity else ""}>${maturity}</option>
        % endfor
      </select></label></p>
      % if error == "blank_maturity":
      <p class="error">Please choose a maturity for your prompt.</p>
      % endif
      <p><label>Trigger warnings: <input type="text" class="full" name="trigger" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("trigger", "")}"></label></p>
      <p class="types">
        % for tag_type in Tag.type_names:
        <label><input type="checkbox" name="type_${tag_type}"${" checked" if "type_" + tag_type in form_data else ""}> ${tag_type}</label>
        % endfor
      </p>
      <hr>
      <h3>Who you're playing</h3>
      <p><label>Character: <input type="text" class="full" name="character" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("character", "")}"></label></p>
      <p><label>Fandom: <input type="text" class="full" name="fandom" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("fandom", "Homestuck")}"></label></p>
      <p><label>Gender: <input type="text" class="full" name="gender" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("gender", "")}"></label></p>
      <hr>
      <h3>Who you're looking for</h3>
      <p><label>Character: <input type="text" class="full" name="character_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("character_wanted", "")}"></label></p>
      <p><label>Fandom: <input type="text" class="full" name="fandom_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("fandom_wanted", "Homestuck")}"></label></p>
      <p><label>Gender: <input type="text" class="full" name="gender_wanted" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("gender_wanted", "")}"></label></p>
      <hr>
      <h3>Other tags</h3>
      <p><input type="text" class="full" name="misc" maxlength="100" placeholder="Enter tags, separated by commas..." value="${form_data.get("misc", "")}"></p>
      <hr>
      <h3>Scenario</h3>
      <p><textarea name="scenario" placeholder="Enter OOC notes here...">${form_data.get("scenario", "")}</textarea></p>
      % if error == "blank_scenario_and_prompt":
      <p class="error">Please write a scenario and/or prompt.</p>
      % endif
      <hr>
      <h3>Prompt</h3>
      <p><input type="color" name="colour" size="6" maxlength="7" value="${form_data.get("colour") or "#000000"}"> <select name="preset_colours">
        % for hex, name in preset_colours:
        <option value="#${hex}">${name}</option>
        % endfor
      </select></p>
      % if error == "invalid_colour":
      <p class="error">Invalid text colour. The colour needs to be a 6-digit hex code.</p>
      % endif
      <p><textarea name="prompt" placeholder="Enter your prompt..." style="color: ${form_data.get("colour") or "#000000"}">${form_data.get("prompt", "")}</textarea></p>
      <hr>
      <div class="actions">
        <div class="right"><input type="submit" name="draft" value="Save draft"> · <input type="submit" name="publish" value="Publish"></div>
      </div>
    </form>
