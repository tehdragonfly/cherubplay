<%inherit file="base.mako" />\
% if request.user.status=="banned":
  <h2>Banned</h2>
  <p>Your account has been banned. If you have seen the error of your ways, please beg for forgiveness in <a href="http://cherubplay.tumblr.com/ask">our ask box</a>.</p>
% else:
  <section id="connecting">
    <h2>Connecting...</h2>
    <noscript>
      <p>It seems you have Javascript disabled. Searching requires Javascript, so you'll need to enable it or swich to a different browser in order to find a roleplaying partner.</p>
    </noscript>
  </section>
  <section id="answer_mode">
    <h2>Answer mode</h2>
    <p>The following people are searching for chats. Answer one of the prompts below or switch to prompt mode to input your own prompt.</p>
    <p>
      <label>Category: <select id="answer_category" name="answer_category">
% for id, name in prompt_categories.items():
        <option value="${id}">${name}</option>
% endfor
      </select> (<a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">?</a>)</label>
      <button class="prompt_button">Switch to prompt mode</button>
    </p>
    <ul id="prompt_list"></ul>
  </section>
  <section id="prompt_mode">
    <h2>Prompt mode</h2>
    <p>Enter a prompt below, and other people will be able to see it and answer if they're interested. Alternatively you can see and respond to other people's prompts in answer mode.</p>
    <p><strong>We've clarified <a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under">what belongs under each category</a>, so please read this to make sure you're posting in the right place.</strong></p>
    <form class="tile">
      <p><input type="color" id="prompt_colour" size="6" value="#000000" maxlength="7"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select></p>
      <p><textarea id="prompt_text" placeholder="Enter your prompt..."></textarea></p>
      <p><label>Post to: <select id="prompt_category" name="prompt_category">
% for id, name in prompt_categories.items():
        <option value="${id}">${name}</option>
% endfor
      </select> (<a href="http://cherubplay.tumblr.com/post/85827459447/heres-a-little-expansion-on-what-belongs-under" target="_blank">?</a>)</label><button type="submit" id="post_button">Post</button></p>
    </form>
    <p><button class="answer_button">Switch to answer mode</button></p>
  </section>
  <section id="wait_mode">
    <h2>Waiting for an answer</h2>
    <p>Your prompt has been posted. Please wait for an answer.</p>
    <p><button class="prompt_button">Edit prompt</button> <button class="answer_button">Switch to answer mode</button></p>
  </section>
  <section id="connection_error">
    <h2>Connection error</h2>
    <p>The connection to the server has been lost. Please refresh the page to try again.</p>
  </section>
  <section id="overlay">
    <section id="overlay_tile" class="tile">
      <p id="overlay_text"></p>
      <button id="overlay_close">Close</button>
      <button id="overlay_report">Report</button>
      <button id="overlay_answer">Answer</button>
    </section>
  </section>
<%block name="scripts"><script>cherubplay.home();</script></%block>
% endif
