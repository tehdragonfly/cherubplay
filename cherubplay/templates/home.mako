<%inherit file="base.mako" />\
% if request.user.status=="banned":
  <h2>banned</h2>
  <p>what the fuck man</p>
  <p>shit like that just aint acceptable round here</p>
% else:
  <section id="connecting">
    <h2>connecting</h2>
    <noscript>
      <p>your browser doesnt support javascript</p>
      <p>haha wow that is so lame</p>
    </noscript>
  </section>
  <section id="answer_mode">
    <h2>answer mode</h2>
    <p>check out these sweet prompts</p>
    <p>
      <label><input type="checkbox" id="show_nsfw"> show nsfw prompts</label>
      <button class="prompt_button">switch to prompt mode</button>
    </p>
    <ul id="prompt_list"></ul>
  </section>
  <section id="prompt_mode">
    <h2>prompt mode</h2>
    <p>in prompt mode</p>
    <p>you are the star</p>
    <p>its you</p>
    <p>and then the big man answers</p>
    <p>but it turns out to be crazy what kind of responses this guy has</p>
    <p>the chat is on fire</p>
    <p>nah im kidding theyll probably just disconnect straight away</p>
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
    <p>your prompt has been posted</p>
    <p>wait here for an answer</p>
    <p><button class="prompt_button">edit prompt</button> <button class="answer_button">switch to answer mode</button></p>
  </section>
  <section id="connection_error">
    <h2>connection error</h2>
    <p>the connection to the server was lost</p>
    <p>looks like your network cant handle this level of awesome</p>
    <p>you need to ditch your internet service provider and replace it with an irony service provider</p>
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
