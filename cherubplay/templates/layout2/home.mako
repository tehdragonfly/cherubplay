<%inherit file="base.mako" />\
<%block name="body_class">layout2</%block>
<main>
% if request.user.status=="banned":
  <h2>Banned</h2>
% if request.user.unban_date is not None:
<% unban_delta = request.user.unban_delta %>
  <p>Your account has been banned. Time until this ban expires: ${str(unban_delta).split(".")[0]}.</p>
% if unban_delta.days != 0:
  <p>If you have seen the error of your ways, please beg for forgiveness in <a href="http://cherubplay.tumblr.com/ask">our ask box</a>.</p>
% endif
% else:
  <p>Your account has been banned. If you have seen the error of your ways, please beg for forgiveness in <a href="http://cherubplay.tumblr.com/ask">our ask box</a>.</p>
% endif
% else:
  <section id="connecting">
    <h2>Connecting...</h2>
    <noscript>
      <p>It seems you have Javascript disabled. Searching requires Javascript, so you'll need to enable it or swich to a different browser in order to find a roleplaying partner.</p>
    </noscript>
  </section>
  <section id="answer_mode">
    <h2>Answer mode</h2>
    <p>The following people are searching for a roleplaying partner. Answer one of the prompts below or post your own.</p>
    <section id="categories" class="tile2">
      <ul id="answer_categories">
% for id, name in prompt_categories.items():
        <li><label><input type="checkbox" name="${id}"> ${name}</label></li>
% endfor
      </ul>
      <ul id="answer_starters">
% for id, name in prompt_starters.items():
        <li><label><input type="checkbox" name="${id}"> ${name}</label></li>
% endfor
      </ul>
      <ul id="answer_levels">
% for id, name in prompt_levels.items():
        <li><label><input type="checkbox" name="${id}"> ${name}</label></li>
% endfor
      </ul>
      <input type="checkbox" id="filter_toggle">
      <p><label for="filter_toggle">Set custom filters</label></p>
      <form>
        <h3>Custom filters</h3>
        <ul id="filter_sites">
          <li><label><input type="checkbox" name="msparp"> Hide MSPARP links</label></li>
          <li><label><input type="checkbox" name="tumblr"> Hide Tumblr links</label></li>
        </ul>
        <p><textarea id="filter_custom" rows="1" placeholder="Hide other phrases..."></textarea></p>
        <button type="submit" id="filter_button">Apply</button>
      </form>
    </section>
    <p class="actions">
      <span class="left"><a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">Category rules</a></span>
      <span class="right"><button class="prompt_button">Post a prompt</button></span>
    </p>
    <ul id="prompt_list"></ul>
  </section>
  <section id="prompt_mode">
    <h2>Prompt mode</h2>
    <p>Enter a prompt below, and other people will be able to see it and answer if they're interested.</p>
    <p><strong>We've clarified <a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under">what belongs under each category</a>, so please read this to make sure you're posting in the right place.</strong></p>
    <form class="tile2">
      <p>We've changed how prompts are categorised. Please <a href="${request.route_path("prompt_list")}">visit your prompts page</a> to make sure they have the right categories selected.</p>
% if saved_prompts:
      <ul>
        <li><label><input type="radio" id="saved_prompt" name="new_or_saved" value="saved" checked="checked"> Use a saved prompt:</label> <select id="prompt_id">
% for prompt in saved_prompts:
          <option value="${prompt.id}">${prompt.title}</option>
% endfor
        </select></li>
        <li><label><input type="radio" id="new_prompt" name="new_or_saved" value="new"> Write a new prompt</label></li>
      </ul>
      <hr>
% endif
      <section id="prompt_info">
        <p><input type="color" id="prompt_colour" size="6" value="#000000" maxlength="7"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select></p>
        <p><textarea id="prompt_text" placeholder="Enter your prompt..."></textarea></p>
        <div id="prompt_dropdowns">Post to:
          <select id="prompt_category" name="prompt_category">
            <option value="">Category...</option>
% for id, name in prompt_categories.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
          <select id="prompt_starter" name="prompt_starter">
            <option value="">Starter?</option>
% for id, name in prompt_starters.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
          <select id="prompt_level" name="prompt_level">
            <option value="">Level...</option>
% for id, name in prompt_levels.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
          (<a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">?</a>)
          <hr>
        </div>
      </section>
      <div class="actions">
        <div class="right"><button type="submit" id="post_button">Post</button></div>
      </div>
    </form>
    <p><button class="answer_button">Back to available prompts</button></p>
  </section>
  <section id="wait_mode">
    <h2>Searching...</h2>
    <p>Your prompt has been posted. Stick around while people look at it - it'll only stay up while you have this tab open.</p>
    <p><button class="prompt_button">Edit prompt</button> <button class="answer_button">Back to available prompts</button></p>
    % if not request.user.email_verified:
    <p class="banner">Remember to <a href="${request.route_path("account")}" target="_blank">set up an e-mail address</a>. If you ever forget your password, we can use it to send you a new one.</p>
    % endif
  </section>
  <section id="connection_error">
    <h2>Connection error</h2>
    <p>The connection to the server has been lost. Please refresh the page to try again.</p>
  </section>
  <section id="overlay">
    <section class="tile2">
      <p id="overlay_text"></p>
    </section>
    <section id="overlay_images"></section>
    <section class="tile2 actions">
      <div class="left"><button id="overlay_close">Close</button> · <button id="overlay_report">Report</button></div>
      <div class="right"><button id="overlay_answer">Answer</button></div>
    </section>
  </section>
  <section id="report_overlay">
    <section class="tile2">
      <p>This prompt is...</p>
      <ul>
        <li>
          <label><input type="radio" name="report_reason" value="wrong_category"> In the wrong category. It should be in</label>
          <select id="report_category">
% for id, name in prompt_categories.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
          <select id="report_starter">
% for id, name in prompt_starters.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
          <select id="report_level">
% for id, name in prompt_levels.items():
            <option value="${id}">${name}</option>
% endfor
          </select>
        </li>
        <li><label><input type="radio" name="report_reason" value="spam"> Spam</label></li>
        <li><label><input type="radio" name="report_reason" value="stolen"> Stolen</label></li>
        <li><label><input type="radio" name="report_reason" value="multiple"> Posted multiple times (if this is the case, please report all instances of it)</label></li>
        <li><label><input type="radio" name="report_reason" value="advert"> Advertising something not related to roleplay</label></li>
        <li><label><input type="radio" name="report_reason" value="ooc"> Soliciting real life or out-of-character interactions</label></li>
      </ul>
      <div class="actions">
        <div class="left"><button id="report_overlay_close">Close</button></div>
       <div class="right"><button id="report_overlay_submit">Submit</button></div>
      </div>
    </section>
  </section>
<%block name="scripts"><script>cherubplay.home();</script></%block>
% endif
</main>
