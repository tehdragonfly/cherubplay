<%inherit file="base.mako" />\
<%block name="heading">New request</%block>
    <form id="new_request_form" class="tile2" action="${request.route_path("directory_new")}" method="post">
      <p><label><select name="maturity">
        <option name="safe_for_work">Safe for work</option>
        <option name="not_safe_for_work">Not safe for work</option>
        <option name="nsfw_extreme">NSFW extreme</option>
      </select></label></p>
      <p><label>Trigger warnings: <input type="text" class="full" name="trigger" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <p class="types">
        <label><input type="checkbox" name="type_fluff"> Fluff</label>
        <label><input type="checkbox" name="type_plot-driven"> Plot-driven</label>
        <label><input type="checkbox" name="type_sexual"> Sexual</label>
        <label><input type="checkbox" name="type_shippy"> Shippy</label>
        <label><input type="checkbox" name="type_violent"> Violent</label>
      </p>
      <h3>Who you're playing</h3>
      <p><label>Character: <input type="text" class="full" name="character" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <p><label>Fandom: <input type="text" class="full" name="fandom" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <p><label>Gender: <input type="text" class="full" name="gender" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <hr>
      <h3>Who you're looking for</h3>
      <p><label>Character: <input type="text" class="full" name="character_wanted" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <p><label>Fandom: <input type="text" class="full" name="fandom_wanted" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <p><label>Gender: <input type="text" class="full" name="gender_wanted" maxlength="100" placeholder="Enter tags, separated by commas..."></label></p>
      <hr>
      <h3>Other tags</h3>
      <p><input type="text" class="full" name="misc" maxlength="100" placeholder="Enter tags, separated by commas..."></p>
      <hr>
      <h3>Scenario</h3>
      <p><textarea name="scenario" placeholder="Enter OOC notes here...">${request.POST.get("scenario", "")}</textarea></p>
      <hr>
      <h3>Prompt</h3>
      <p><input type="color" name="colour" size="6" maxlength="7" value="${request.POST.get("prompt_colour") or "#000000"}"> <select name="preset_colours">
% for hex, name in preset_colours:
        <option value="#${hex}">${name}</option>
% endfor
      </select></p>
      <p><textarea name="prompt" placeholder="Enter your prompt...">${request.POST.get("prompt", "")}</textarea></p>
      <hr>
      <input type="submit" name="publish" value="Publish">
      <input type="submit" name="draft" value="Save draft">
      <br class="clear">
    </form>
