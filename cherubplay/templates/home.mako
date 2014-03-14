<%inherit file="base.mako" />\
% if request.user.status=="banned":
  <h2>banned</h2>
  <p>Your account has been banned. If you have seen the error of your ways, please beg for forgiveness in <a href="http://cherubplay.tumblr.com/ask">our ask box</a>.</p>
% else:
  <section id="connecting">
    <h2>connecting</h2>
    <noscript>
      <p>It seems you have Javascript disabled. Searching requires Javascript, so you'll need to enable it or swich to a different browser in order to find a roleplaying partner.</p>
    </noscript>
  </section>
  <section id="answer_mode">
    <h2>answer mode</h2>
    <p>The following people are searching for chats. Answer one of the prompts below or switch to prompt mode to input your own prompt.</p>
    <p>
      <label><input type="checkbox" id="show_nsfw"> show nsfw prompts</label>
      <button class="prompt_button">switch to prompt mode</button>
    </p>
    <ul id="prompt_list"></ul>
  </section>
  <section id="prompt_mode">
    <h2>prompt mode</h2>
    <p>Enter a prompt below, and other people will be able to see it and answer if they're interested. Alternatively you can see and respond to other people's prompts in answer mode.</p>
    <form class="tile">
      <p><input type="color" id="prompt_colour" size="6" value="#E00707" maxlength="7"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select><label><input type="checkbox" id="prompt_nsfw"> nsfw</label></p>
      <p><textarea id="prompt_text" placeholder="enter your prompt"></textarea></p>
      <button type="submit">search</button>
    </form>
    <p><button class="answer_button">switch to answer mode</button></p>
  </section>
  <section id="wait_mode">
    <h2>waiting for an answer</h2>
    <p>Your prompt has been posted. Please wait for an answer.</p>
    <p><button class="prompt_button">edit prompt</button> <button class="answer_button">switch to answer mode</button></p>
  </section>
  <section id="connection_error">
    <h2>connection error</h2>
    <p>The connection to the server has been lost. Please refresh the page to try again.</p>
  </section>
  <section id="overlay">
    <section id="overlay_tile" class="tile">
      <p id="overlay_text"></p>
      <button id="overlay_close">close</button>
      <button id="overlay_answer">answer</button>
    </section>
  </section>
<%block name="scripts"><script>cherubplay.home();</script></%block>
% endif
